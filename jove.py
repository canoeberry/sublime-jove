#
# Figure out if you can make escaping from incremental search built-in by just specifying the names of commands you want
# to escape with. The on_text_command listener can close up the isearch and run the command on a different view
# (maybe?). Can you just rewrite the command and let "JoveIncSearchEscape" do the work?

# IMPLEMENT
#
# - implement mark ring instead of just the mark
# - implement a build command which lets me specify the make command I want to run
# - implement forward/backward "defun" via scope selectors
# - implement forward/backward class definition via scope selectors
# - delete blank lines would be nice
# - quit command should erase the main selection as well

# FIX
#
# fix window commands - make your own split window stuff so you can implement next/prev properly (the ordering is messed
# up - not sorted)
#
# fix tab so that if you're in the whitespace, it moves to first non-blank
#
# fix comments so you can comment in the right column if no region is selected

# make sexpressions work, including moving over balanced parens and quotes
#

# Fix indent and deindent not to require the selection. Instead, it should use the region.

import functools as fu
import sublime
import sublime_plugin
from copy import copy
import re, sys

JOVE_STATUS = "jove"

ISEARCH_ESCAPE_CMDS = ('move_to', 'jove_center_view', 'move', 'jove_universal_argument',
                       'jove_move_word', 'jove_move_to')

#
# We store state about each view.
#
class ViewState():
    # per view state
    view_state_dict = dict()

    # currently active view
    current = None

    # currently incremental search instance
    isearch_info = None

    # initialized at the end of this file after all commands are defined
    kill_cmds = set()

    # ensure_visible commands
    ensure_visible_cmds = set(['move', 'move_to'])

    # repeatable commands
    repeatable_cmds = set(['move', 'left_delete', 'right_delete'])

    def __init__(self, view):
        self.view = view
        self.active_mark = False
        self.reset()

    @classmethod
    def for_view(cls, view):
        state = cls.view_state_dict.get(view.id(), None)
        if state is None:
            state = ViewState(view)
            cls.view_state_dict[view.id()] = state
            state.view = view
        return state

    @classmethod
    def on_view_closed(cls, view):
        if view.id() in cls.view_state_dict:
            del(cls.view_state_dict[view.id()])

    @staticmethod
    def ensure_view(view):
        # make sure current is set to this view
        if ViewState.current is None or ViewState.current.view != view:
            ViewState.current = ViewState.for_view(view)

    def reset(self):
        self.this_cmd = None
        self.last_cmd = None
        self.argument_supplied = False
        self.argument_value = 0
        self.argument_negative = False
        self.drag_count = 0

    #
    # Get the argument count and reset it for the next command (unless peek is True).
    #
    def get_count(self, peek=False):
        if self.argument_supplied:
            count = self.argument_value
            if self.argument_negative:
                count = -count
                if not peek:
                    self.argument_negative = False
            if not peek:
                self.argument_supplied = False
        else:
            count = 1
        return count

    def last_was_kill_cmd(self):
        return self.last_cmd in self.kill_cmds

class ViewWatcher(sublime_plugin.EventListener):
    def on_close(self, view):
        ViewState.on_view_closed(view)

    def on_modified(self, view):
        CmdMixin(view).toggle_active_mark_mode(False)

    def on_deactivated(self, view):
        info = ViewState.isearch_info
        if info and info.input_view == view:
            # deactivate immediately or else overlays will malfunction (we'll eat their keys)
            # we cannot dismiss the input panel because an overlay (if present) will lose focus
            info.deactivate()

    def on_activated_async(self, view):
        info = ViewState.isearch_info
        if info and not view.settings().get("is_widget"):
            # now we can dismiss the input panel
            info.done()

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "i_search_active":
            return ViewState.isearch_info and ViewState.isearch_info.is_active

class CmdWatcher(sublime_plugin.EventListener):
    def on_anything(self, view):
        view.erase_status(JOVE_STATUS)

    #
    # Override some commands to execute them N times if the numberic argument is supplied.
    #
    def on_text_command(self, view, cmd, args):
        if view.settings().get('is_widget') and ViewState.isearch_info:
            if cmd in ISEARCH_ESCAPE_CMDS:
                return ('jove_inc_search_escape', {'next_cmd': cmd, 'next_args': args})
            return

        ViewState.ensure_view(view)
        self.on_anything(view)

        if args is None:
            args = {}

        vs = ViewState.current

        # first keep track of this_cmd and last_cmd (if command starts with "jove_" it's handled elsewhere)
        if not cmd.startswith("jove_"):
            vs.this_cmd = cmd

        #
        #  Process events that create a selection. The hard part is making it work with the emacs region.
        #
        if cmd == 'drag_select':
            if ViewState.isearch_info:
                ViewState.isearch_info.cancel()

            # Set drag_count to 0 when drag_select command occurs. BUT, if the 'by' parameter is present, that means a
            # double or triple click occurred. When that happens we have a selection we want to start using, so we set
            # drag_count to 2. 2 is the number of drag_counts we need in the normal course of events before we turn
            # on the active mark mode.
            vs.drag_count = 2 if 'by' in args else 0

        if cmd in ('move', 'move_to') and vs.active_mark and not args.get('extend', False):
            args['extend'] = True
            return (cmd, args)

        # now check for numeric argument and rewrite some commands as necessary
        if not vs.argument_supplied:
            return

        if cmd in vs.repeatable_cmds:
            count = vs.get_count()
            args.update({
                'cmd': cmd,
                '_times': abs(count),
            })
            if count < 0 and 'forward' in args:
                args['forward'] = not args['forward']
            return ("jove_do_times", args)
        elif cmd == 'scroll_lines':
            args['amount'] *= vs.get_count()
            return (cmd, args)

    #
    # Post command processing: deal with active mark and resetting the numeric argument.
    #
    def on_post_text_command(self, view, cmd, args):
        ViewState.ensure_view(view)
        vs = ViewState.current
        if vs.active_mark and vs.this_cmd != 'drag_select' and vs.last_cmd == 'drag_select':
            # if we just finished a mouse drag, make sure active mark mode is off
            CmdMixin(view).toggle_active_mark_mode(False)

        # reset numeric argument (if command starts with "jove_" this is handled elsewhere)
        if not cmd.startswith("jove_"):
            vs.argument_value = 0
            vs.argument_supplied = False
            vs.last_cmd = cmd

        self.update_status(view)

        cm = CmdMixin(view)

        if vs.active_mark:
            cm.set_selection(cm.get_mark(), cm.get_point())

        if cmd in ViewState.ensure_visible_cmds and cm.just_one_point():
            cm.ensure_visible(cm.get_point())

    #
    # Process the selection if it was created from a drag_select (mouse dragging) command.
    #
    def on_selection_modified(self, view):
        vs = ViewState.current
        selection = view.sel()

        if len(selection) == 1 and vs.this_cmd == 'drag_select':
            cm = CmdMixin(view);
            if vs.drag_count == 2:
                # second event - enable active mark
                region = view.sel()[0]
                mark = region.a
                cm.set_mark(mark, and_selection=False)
                cm.toggle_active_mark_mode(True)
            elif vs.drag_count == 0:
                cm.toggle_active_mark_mode(False)
        vs.drag_count += 1


    #
    # At a minimum this is called when bytes are inserted into the buffer.
    #
    def on_modified(self, view):
        ViewState.current.this_cmd = None
        self.update_status(view)
        self.on_anything(view)

    #
    # REMIND: Not really used anymore.
    #
    def update_status(self, view):
        if ViewState.current.argument_supplied:
            s = "-" if ViewState.current.argument_negative else ""
            if ViewState.current.argument_value != 0:
                s = s + str(ViewState.current.argument_value)

#
# Classic emacs kill ring.
#
class KillRing:
    KILL_RING_SIZE = 64

    def __init__(self):
        self.buffers = [None] * self.KILL_RING_SIZE
        self.index = 0

    #
    # Add some text to the kill ring. 'forward' indicates whether the editing command that produced this data was in the
    # forward or reverse direction. It only matters if 'join' is true, because it tells us how to add this data to the
    # most recent kill ring entry rather than creating a new entry.
    #
    def add(self, text, forward, join):
        if len(text) == 0:
            return
        buffers = self.buffers
        index = self.index
        if not join:
            index += 1
            if index >= len(buffers):
                index = 0
            self.index = index
            buffers[index] = text
        else:
            if buffers[index] is None:
                buffers[index] = text
            elif forward:
                buffers[index] = buffers[index] + text
            else:
                buffers[index] = text + buffers[index]
        sublime.set_clipboard(buffers[index])

    #
    # Returns the current entry in the kill ring. If pop is non-zero, we move backwards or forwards once in the kill
    # ring and return that data instead.
    #
    def get_current(self, pop):
        buffers = self.buffers
        index = self.index

        if pop == 0:
            clipboard = sublime.get_clipboard()
            val = buffers[index]
            if val != clipboard and clipboard:
                # we switched to another app and cut or copied something there, so add that to our kill ring
                self.add(clipboard, True, False)
                val = clipboard
        else:
            incr = self.KILL_RING_SIZE - 1 if pop == 1 else 1
            index = (index + incr) % self.KILL_RING_SIZE
            while buffers[index] is None and index != self.index:
                index = (incr + index) % self.KILL_RING_SIZE
            self.index = index
            val = buffers[index]
            sublime.set_clipboard(val)

        return val

#
# A mixin class which provides a bunch of useful functionality on a view, which is stored as an instance
# variable. sublime_plugin.TextCommand has its own view instance variable which this class makes use of when
# mixed in with TextCommand.
#
class CmdMixin:
    class_names = {
        sublime.CLASS_WORD_START: 'word_start',
        sublime.CLASS_WORD_END: 'word_end',
        sublime.CLASS_PUNCTUATION_START: 'punct_start',
        sublime.CLASS_PUNCTUATION_END: 'punct_end',
        sublime.CLASS_SUB_WORD_START: 'sub_word_start',
        sublime.CLASS_SUB_WORD_END: 'sub_word_end',
        sublime.CLASS_LINE_START: 'line_start',
        sublime.CLASS_LINE_END: 'line_end',
        sublime.CLASS_EMPTY_LINE: 'empty_line',
        512: 'mid_word',
    }

    def __init__(self, view=None):
        if view:
            self.view = view

    def get_type_string(self, type):
        vals = []
        for bit,name in self.class_names.items():
            if (type & bit) != 0:
                vals.append(name)
        return ",".join(vals)


    #
    # Sets the status text on the bottom of the window.
    #
    def set_status(self, msg):
        self.view.set_status(JOVE_STATUS, msg)

    #
    # Returns point. Point is where the cursor is in the possibly extended region. If there are multiple cursors it
    # uses the first one in the list.
    #
    def get_point(self):
        sel = self.view.sel()
        if len(sel) > 0:
            return sel[0].b
        return -1

    def get_mark(self):
        mark = self.view.get_regions("jove_mark")
        if mark:
            mark = mark[0]
            return mark.a

    def get_jove_region(self):
        selection = self.view.sel()
        if len(selection) != 1:
            # Oops - this error message does not belong here!
            self.set_status("Cannot kill region with multiple cursors")
            return
        selection = selection[0]
        if selection.size() > 0:
            return selection
        mark = self.get_mark()
        if mark is not None:
            point = self.get_point()
            return sublime.Region(mark, self.get_point())

    def set_mark(self, pos=None, update_status=True, and_selection=True):
        view = self.view

        if pos is None:
            pos = self.get_point()
        mark = sublime.Region(pos, pos)
        view.add_regions("jove_mark", [mark], "mark", "dot", sublime.HIDDEN | sublime.PERSISTENT)
        if and_selection:
            self.set_selection(pos, pos)
        if update_status:
            self.set_status("Mark Saved")

    #
    # Enabling active mark means highlight the current emacs region.
    #
    def toggle_active_mark_mode(self, value=None):
        if value is not None and ViewState.current.active_mark == value:
            return

        ViewState.current.active_mark = value if value is not None else (not ViewState.current.active_mark)
        point = self.get_point()
        if ViewState.current.active_mark:
            mark = self.get_mark()
            self.set_selection(mark, point)
            ViewState.current.active_mark = True
        else:
            self.set_selection(point, point)

    def swap_point_and_mark(self):
        view = self.view
        mark = self.get_mark()
        if mark is not None:
            if ViewState.current.active_mark:
                region = view.sel()[0]
                self.set_selection(region.b, region.a)
                self.ensure_visible(region.a)
                self.set_mark(region.b, update_status=False, and_selection=False)
            else:
                point = self.get_point()
                self.set_mark(point, update_status=False)
                self.goto_position(mark)
        else:
            self.set_status("No mark in this buffer")

    def set_selection(self, a=None, b=None):
        if a is None:
            a = b = self.get_point()
        selection = self.view.sel()
        selection.clear()
        selection.add(sublime.Region(a, b))

    def get_line_info(self, point):
        view = self.view
        region = view.line(point)
        data = view.substr(region)
        row,col = view.rowcol(point)
        return (data, col, region)

    def run_window_command(self, cmd, args):
        self.view.window().run_command(cmd, args)

    def has_prefix_arg(self):
        return ViewState.current.argument_supplied

    def just_one_point(self):
        return len(self.view.sel()) == 1

    def get_count(self, peek=False):
        return ViewState.current.get_count(peek)

    #
    # A way to run a command in the context of each of the current cursors. The end result is that all the cursors are
    # updated based on the return value from each invokation of the command.
    #
    def for_each_cursor(self, function, edit=None, *args, **kwargs):
        view = self.view
        settings = view.settings()
        selection = view.sel()

        # run the command passing in each cursor and collecting the returned cursor
        new_cursors = [function(cursor, edit=edit, *args, **kwargs) for cursor in selection]
        cleared = False
        for cursor in new_cursors:
            if cursor is not None:
                if not cleared:
                    selection.clear()
                    cleared = True
                selection.add(cursor)

    def goto_line(self, line):
        if line >= 0:
            view = self.view
            point = view.text_point(line - 1, 0)
            self.goto_position(point, set_mark=True)

    def goto_position(self, point, set_mark=False):
        if set_mark and self.get_point() != point:
            self.set_mark()
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point, point))
        self.ensure_visible(point)

    def delete_at(self, regex):
        pass

    def skip_chars(self, regex, dir):
        pass

    def is_visible(self, pos):
        visible = self.view.visible_region()
        return visible.contains(pos)

    def ensure_visible(self, point, force=False):
        if force or not self.is_visible(point):
            self.view.show_at_center(point)

    def is_word_char(self, pos, forward, separators):
        if not forward:
            if pos == 0:
                return False
            pos -= 1
        char = self.view.substr(pos)
        return not (char in " \t\r\n" or char in separators)

#
# here we put a bunch of useful helpers for moving around and manipulating buffers
#
class JoveTextCommand(CmdMixin, sublime_plugin.TextCommand):
    kill_ring = KillRing()                        # class variable
    is_kill_cmd = False
    is_ensure_visible_cmd = False
    unregistered = False

    def run(self, edit, **kwargs):
        ViewState.ensure_view(self.view)

        vs = ViewState.current

        # first keep track of this_cmd and last_cmd
        cmd = self.jove_cmd_name
        if cmd != 'jove_universal_argument' or self.unregistered:
            vs.this_cmd = cmd

        self.run_cmd(edit, **kwargs)

        if cmd != 'jove_universal_argument' or self.unregistered:
            vs.last_cmd = cmd
            vs.argument_value = 0
            vs.argument_supplied = False

class JoveDoTimesCommand(JoveTextCommand):
    def run_cmd(self, edit, cmd, _times, **args):
        view = self.view
        visible = view.visible_region()
        for i in range(_times):
            view.run_command(cmd, args)
        point = self.get_point()
        if not visible.contains(point):
            self.ensure_visible(point, True)

class JoveShowScopeCommand(JoveTextCommand):
    def run_cmd(self, edit, direction=1):
        name = self.view.scope_name(self.get_point())
        region = self.view.extract_scope(self.get_point())
        self.view.set_status(JOVE_STATUS, "%d bytes: %s" % (region.size(), name))

class JoveMoveWordCommand(JoveTextCommand):
    is_ensure_visible_cmd = True

    def run_cmd(self, edit, direction=1, is_sexpr=False):
        view = self.view

        settings = view.settings()
        separators = None
        if is_sexpr:
            separators = settings.get("jove_sexpr_separators")
        if separators is None:
            separators = settings.get("jove_word_separators")

        # determine the direction
        count = self.get_count() * direction
        forward = count > 0
        count = abs(count)

        def move_word0(cursor, first=False, **kwargs):
            point = cursor.b
            if forward:
                if not first or not self.is_word_char(point, True, separators):
                    point = view.find_by_class(point, True, sublime.CLASS_WORD_START, separators)
                point = view.find_by_class(point, True, sublime.CLASS_WORD_END, separators)
            else:
                if not first or not self.is_word_char(point, False, separators):
                    point = view.find_by_class(point, False, sublime.CLASS_WORD_END, separators)
                point = view.find_by_class(point, False, sublime.CLASS_WORD_START, separators)
            cursor.a = cursor.b = point
            return cursor

        for c in range(count):
            self.for_each_cursor(move_word0, first=(c == 0))

class JoveGotoLineCommand(JoveTextCommand):
    def run_cmd(self, edit):
        if self.has_prefix_arg():
            self.goto_line(self.get_count())
        else:
            self.run_window_command("show_overlay", {"overlay": "goto", "text": ":"})

class JoveMoveSexprCommand(JoveMoveWordCommand):
    def run_cmd(self, edit, direction=1):
        super(JoveMoveSexprCommand, self).run(edit, direction, True)

class JoveDeleteWordCommand(JoveTextCommand):
    is_ensure_visible_cmd = True
    is_kill_cmd = True

    def run_cmd(self, edit, direction=1):
        view = self.view
        selection = view.sel()
        count = self.get_count(True) * direction

        # remember the current cursor positions
        orig_cursors = [s for s in selection]

        view.run_command("jove_move_word", {"direction": direction})

        # extend each cursor so we can delete the bytes, and only if there is only one region will we add the data to
        # the kill ring
        new_cursors = [s for s in selection]

        selection.clear()
        for old,new in zip(orig_cursors, new_cursors):
            if old < new:
                selection.add(sublime.Region(old.begin(), new.end()))
            else:
                selection.add(sublime.Region(new.begin(), old.end()))

        # only append to kill ring if there's one selection
        if len(selection) == 1:
            self.kill_ring.add(view.substr(selection[0]), forward=count > 0, join=ViewState.current.last_was_kill_cmd())

        for region in selection:
            view.erase(edit, region)

class JoveDeleteWhiteSpaceCommand(JoveTextCommand):
    """Deletes white space around point like in emacs."""

    def run_cmd(self, edit):
        self.for_each_cursor(self.delete_white_space, edit=edit)

    def delete_white_space(self, cursor, edit, **kwargs):
        view = self.view
        line = view.line(cursor.a)
        data = view.substr(line)
        row,col = view.rowcol(cursor.a)
        start = col
        while start - 1 >= 0 and data[start-1: start] in (" ", "\t"):
            start -= 1
        end = col
        limit = len(data)
        while end + 1 < limit and data[end:end+1] in (" ", "\t"):
            end += 1
        view.erase(edit, sublime.Region(line.begin() + start, line.begin() + end))
        return None

# class JoveIndentRegion(JoveTextCommand):
#     def run_cmd(self, edit, direction):
#         view = self.view
#         if direction < 0:
#             # deindenting - calculate the minimum indent across all the lines
#             for region in self.for_each_line():

#         if view.get_mark() is not None:
#             view.toggle_active_mark_mode(True)
#             view.run_command("")

class JoveUniversalArgumentCommand(JoveTextCommand):
    def run_cmd(self, edit, value):
        vs = ViewState.current
        if not vs.argument_supplied:
            vs.argument_supplied = True
            if value == 'by_four':
                vs.argument_value = 4
            elif value == 'negative':
                vs.argument_negative = True
            else:
                vs.argument_value = value
        elif value == 'by_four':
            vs.argument_value *= 4
        elif isinstance(value, int):
            vs.argument_value *= 10
            vs.argument_value += value
        elif value == 'negative':
            vs.argument_value = -vs.argument_value

class JoveCenterViewCommand(JoveTextCommand):
    '''
    I prefer old style emacs Control-L behavior: Center the view unless there is an numeric argument, in which case put
    line with the cursor at the numeric argument line number on the screen. Meta-0 Ctrl-L means put the current line at
    the top of the screen.
    '''

    def run_cmd(self, edit):
        view = self.view
        point = self.get_point()
        if self.has_prefix_arg():
            lines = self.get_count()
            line_height = view.line_height()
            ignore, point_offy = view.text_to_layout(point)
            offx, ignore = view.viewport_position()
            view.set_viewport_position((offx, point_offy - line_height * lines))
        else:
            view.show_at_center(point)

class JoveSetMarkCommand(JoveTextCommand):
    def run_cmd(self, edit):
        if ViewState.current.this_cmd == ViewState.current.last_cmd or ViewState.current.argument_supplied:
            # at least two set mark commands in a row: turn ON the highlight
            self.toggle_active_mark_mode()
        else:
            # set the mark
            ViewState.current.active_mark = False
            self.set_mark()

class JoveSwapPointAndMarkCommand(JoveTextCommand):
    def run_cmd(self, edit):
        if ViewState.current.argument_supplied:
            self.toggle_active_mark_mode()
        else:
            self.swap_point_and_mark()

class JoveMoveToCommand(JoveTextCommand):
    is_ensure_visible_cmd = True
    def run_cmd(self, edit, to):
        if to == 'bof':
            self.goto_position(0, set_mark=True)
        elif to == 'eof':
            self.goto_position(self.view.size(), set_mark=True)
        elif to in ('eow', 'bow'):
            visible = self.view.visible_region()
            self.goto_position(visible.a if to == 'bow' else visible.b, True)

class JoveOpenLineCommand(JoveTextCommand):
    def run_cmd(self, edit):
        view = self.view
        for point in view.sel():
            view.insert(edit, point.b, "\n")
        view.run_command("move", {"by": "characters", "forward": False})

class JoveKillRegionCommand(JoveTextCommand):
    is_kill_cmd = True
    def run_cmd(self, edit, is_copy=False):
        view = self.view
        region = self.get_jove_region()
        if region:
            bytes = region.size()
            self.kill_ring.add(view.substr(region), True, False)
            if not is_copy:
                view.erase(edit, region)
            else:
                self.set_status("Copied %d bytes" % (bytes,))
            self.toggle_active_mark_mode(False)

class JoveTravelToPaneCommand(sublime_plugin.WindowCommand):
    def run(self, direction):
        window = sublime.active_window()
        ViewState.current.reset()
        num = window.num_groups()
        active = window.active_group()
        dir = -1 if direction == "up" else 1
        active += dir
        if active >= num:
            active = 0
        elif active < 0:
            active = num - 1
        window.focus_group(active)

class JoveDestroyPanesCommand(sublime_plugin.WindowCommand):
    def run(self, pane):
        window = self.window
        if pane == 'self':
            window.run_command("destroy_pane", {"direction": "self"})
        else:
            window = sublime.active_window()
            active = window.active_group()
            cnt = window.num_groups()
            while window.active_group() > 0 and --cnt >= 0:
                window.run_command("destroy_pane", {"direction": "up"})
            while window.num_groups() > 1 and --cnt >= 0:
                window.run_command("destroy_pane", {"direction": "down"})

class JoveKillLineCommand(JoveTextCommand):
    is_kill_cmd = True
    def run_cmd(self, edit, is_copy=False):
        view = self.view
        start = self.get_point()
        text,index,region = self.get_line_info(start)
        vs = ViewState.current
        if vs.argument_supplied:
            # we don't support negative arguments for kill-line
            count = abs(vs.get_count())

            # go down N lines
            for i in range(abs(count)):
                view.run_command("move", {"by": "lines", "forward": True})

            end = self.get_point()
            if region.contains(end):
                # same line we started on - must be on the last line of the file
                end = region.end()
            else:
                # beginning of the line we ended up on
                end = view.line(self.get_point()).begin()
                self.goto_position(end, set_mark=False)
        else:
            end = region.end()

            # check if line is blank from here to the end
            import re
            if re.match(r'[ \t]*$', text[index:]):
                end += 1

        region = sublime.Region(start, end)
        self.kill_ring.add(view.substr(region), True, vs.last_was_kill_cmd())
        view.erase(edit, region)

class JoveYankCommand(JoveTextCommand):
    def run_cmd(self, edit, pop=0):
        # for now only works with one cursor
        view = self.view
        selection = view.sel()
        if len(selection) != 1:
            self.set_status("Cannot yank with multiple cursors ... yet")
            return

        if pop != 0:
            # we need to delete the existing data first
            if ViewState.current.last_cmd != 'jove_yank':
                self.set_status("Previous command was not yank!")
                return
            view.erase(edit, self.get_jove_region())

        data = self.kill_ring.get_current(pop)
        if data:
            point = self.get_point()
            view.insert(edit, point, data)
            self.set_mark(point, and_selection=False)
        else:
            self.set_status("Nothing to pop!")

#####################################################
#            Better incremental search              #
#####################################################
class ISearchInfo():
    last_search = None

    class StackItem():
        def __init__(self, search, regions, selected, current_index, forward, wrapped):
            self.prev = None
            self.search = search
            self.regions = regions
            self.selected = selected
            self.current_index = current_index
            self.forward = forward
            self.try_wrapped = False
            self.wrapped = wrapped
            if current_index >= 0 and regions:
                # add the new one to selected
                selected.append(regions[current_index])

        def get_point(self):
            if self.current_index >= 0:
                r = self.regions[self.current_index]
                return r.begin() if self.forward else r.end()
            return None

        #
        # Clone is called when we want to make progress with the same search string as before.
        #
        def step(self, forward, keep):
            index = self.current_index
            matches = len(self.regions)
            if (self.regions and (index < 0 or (index == 0 and not forward) or (index == matches - 1) and forward)):
                # wrap around!
                index = 0 if forward else matches - 1
                if self.try_wrapped or not self.regions:
                    wrapped = True
                    self.try_wrapped = False
                else:
                    self.try_wrapped = True
                    return None
            elif (forward and index < matches - 1) or (not forward and index > 0):
                index = index + 1 if forward else index - 1
                wrapped = self.wrapped
            else:
                return None
            selected = copy(self.selected)
            if not keep and len(selected) > 0:
                del(selected[-1])
            return ISearchInfo.StackItem(self.search, self.regions, selected, index, forward, wrapped)


    def __init__(self, view, forward):
        self.view = view
        self.current = ISearchInfo.StackItem("", [], [], -1, forward, False)
        self.helper = CmdMixin(view)
        self.window = view.window()
        self.point = self.helper.get_point()
        self.update()
        self.input_view = None
        self.in_changes = 0
        self.forward = forward
        self.is_active = True

    def is_active(self):
        return ViewState.isearch_info == self

    def on_done(self, val):
        # on_done: stop the search, keep the cursors intact
        ViewState.isearch_info = None
        if self.is_active:
            self.finish(abort=False)

    def on_cancel(self):
        # on_cancel: stop the search, go back to start
        ViewState.isearch_info = None
        if self.is_active:
            self.finish(abort=True)

    def on_change(self, val):
        if self.in_changes > 0:
            # When we pop back to an old state, we have to replace the search string with what was in effect at that
            # state. We do that by deleting all the text and inserting the value of the search string. This causes this
            # on_change method to be called. We want to ignore it, which is what we're doing here.
            self.in_changes -= 1
            return

        # determine if this is case sensitive search or not
        flags = sublime.LITERAL
        if not re.search(r'[A-Z]', val):
            flags |= sublime.IGNORECASE

        # find all instances if we have a search string
        if len(val) > 0:
            regions = self.view.find_all(val, flags)

            # find the closest match to where we currently are
            point = None
            if self.current:
                point = self.current.get_point()
            if point is None:
                point = self.point
            index = self.find_closest(regions, point, self.forward)

            # push this new state onto the stack
            self.push(ISearchInfo.StackItem(val, regions, [], index, self.forward, self.current.wrapped))
        else:
            regions = None
            index = -1
        self.update()

    #
    # Implementation and internal API.
    #

    #
    # Push a new state onto the stack.
    #
    def push(self, item):
        item.prev = self.current
        self.current = item

    #
    # Pop one state of the stack and restore everything to the state at that time.
    #
    def pop(self):
        if self.current.prev:
            self.current = self.current.prev
            self.set_text(self.current.search)
            self.forward = self.current.forward
            self.update()
        else:
            print("NOthing to pop so not updating!")

    def deactivate(self):
        self.is_active = False
        self.finish(abort=False)

    def done(self):
        # close the panel which should trigger an on_done
        self.view.window().run_command("hide_panel")

    #
    # Set the text of the search to a particular value. If is_pop is True it means we're restoring to a previous state.
    # Otherwise, we want to pretend as though this text were actually inserted.
    #
    def set_text(self, text, is_pop=True):
        if is_pop:
            self.in_changes += 1
        self.input_view.run_command("select_all")
        self.input_view.run_command("left_delete")
        self.input_view.run_command("insert", {"characters": text})

    def not_in_error(self):
        si = self.current
        #while si and not si.regions and si.search:
        while si and not si.selected and si.search:
            si = si.prev
        return si

    def finish(self, abort=False):
        if self.current and self.current.search:
            ISearchInfo.last_search = self.current.search
        self.helper.set_status("")

        point_set = False
        if not abort:
            selection = self.view.sel()
            selection.clear()
            current = self.not_in_error()
            if current and current.selected:
                selection.add_all(current.selected)
                point_set = True

        if not point_set:
            # back whence we started
            self.helper.set_selection(self.point)
            self.helper.ensure_visible(self.point)
        else:
            self.helper.set_mark(self.point, and_selection=False)

        # erase our regions
        self.view.erase_regions("find")
        self.view.erase_regions("selected")

    def update(self):
        si = self.not_in_error()
        if si is None:
            return

        self.view.add_regions("find", si.regions, "text", "", sublime.DRAW_NO_FILL)
        selected = si.selected or []
        self.view.add_regions("selected", selected, "string", "", 0)
        if selected:
            self.helper.ensure_visible(selected[-1])

        status = ""
        if si != self.current:
            status += "Failing "
        if self.current.wrapped:
            status += "Wrapped "
        status += "I-Search " + ("Forward" if self.current.forward else "Reverse")
        if si != self.current:
            if len(self.current.regions) > 0:
                status += " %s matches %s" % (len(self.current.regions), ("above" if self.forward else "below"))
        else:
            status += " %d matches, %d cursors" % (len(si.regions), len(si.selected))

        self.helper.set_status(status)

    #
    # Try to make progress with the current search string. Even if we're currently failing (in our current direction) it
    # doesn't mean there aren't matches for what we've typed so far.
    #
    def next(self, keep, forward=None):
        if self.current.prev is None:
            # do something special if we invoke "i-search" twice at the beginning
            if ISearchInfo.last_search:
                # insert the last search string
                self.set_text(ISearchInfo.last_search, is_pop=False)
        else:
            if forward is None:
                forward = self.current.forward
            new = self.current.step(forward=forward, keep=keep)
            if new:
                self.push(new)
                self.update()

    def append_from_cursor(self):
        # Figure out the contents to the right of the last region in the current selected state, and append characters
        # from there.
        si = self.current
        if len(si.search) > 0 and not si.selected:
            # search is failing - no point in adding from current cursor!
            return

        view = self.view
        limit = view.size()
        if si.selected:
            point = si.selected[-1].end()
        else:
            point = self.point
        if point >= limit:
            return

        # now push new states for each character we append to the search string
        helper = self.helper
        search = si.search
        separators = view.settings().get("jove_word_separators")
        case_sensitive = re.search(r'[A-Z]', search) is not None

        # if the first character is a word character, we insert until we hit a non-word character.
        if not helper.is_word_char(point, True, separators):
            self.on_change(search + view.substr(point))
        else:
            while point < limit and helper.is_word_char(point, True, separators):
                ch = view.substr(point)
                if not case_sensitive:
                    ch = ch.lower()
                search += ch
                self.on_change(search)
                point += 1
        self.set_text(self.current.search)

    def cancel(self):
        self.view.window().run_command("hide_panel")
        self.finish(abort=True)

    def quit(self):
        close = False

        if self.current.regions:
            # if we have some matched regions, we're in "successful" state and close down the whole thing
            close = True
        else:
            # here the search is currently failing, so we back up until the last non-failing state
            while self.current.prev and not self.current.prev.regions:
                self.current = self.current.prev
            if self.current.prev is None:
                close = True
        if close:
            self.cancel()
        else:
            self.pop()


    def find_closest(self, regions, pos, forward):
        #
        # The regions are sorted so clearly this would benefit from a simple binary search ...
        #
        if len(regions) == 0:
            return -1
        # find the first region after the specified pos
        found = False
        if forward:
            for index,r in enumerate(regions):
                if r.end() >= pos:
                    return index
            return -1
        else:
            for index,r in enumerate(regions):
                if r.begin() > pos:
                    return index - 1
            return len(regions) - 1

class JoveIncSearchCommand(JoveTextCommand):
    def run_cmd(self, edit, cmd=None, **kwargs):
        info = ViewState.isearch_info
        if info is None:
            info = ViewState.isearch_info = ISearchInfo(self.view, kwargs['forward'])
            window = self.view.window()
            info.input_view = window.show_input_panel("I-Search:", "", info.on_done, info.on_change, info.on_cancel)
        else:
            if cmd == "next":
                info.next(**kwargs)
            elif cmd == "pop":
                info.pop()
            elif cmd == "append_from_cursor":
                info.append_from_cursor()
            else:
                print("Not handling cmd", cmd, kwargs)

class JoveIncSearchEscape(JoveTextCommand):
    unregistered = True
    def run_cmd(self, edit, next_cmd, next_args):
        info = ViewState.isearch_info
        info.done()
        info.view.run_command(next_cmd, next_args)

class JoveQuitCommand(JoveTextCommand):
    def run_cmd(self, edit):
        window = self.view.window()

        if ViewState.isearch_info:
            ViewState.isearch_info.quit()
            return

        for cmd in ['clear_fields', 'hide_overlay', 'hide_auto_complete', 'hide_panel']:
            window.run_command(cmd)

        # If there is a selection, set point to the end of it that is visible.
        s = self.view.sel()
        s = s and s[0]
        if s:
            if self.is_visible(s.b):
                pos = s.b
            elif self.is_visible(s.a):
                pos = s.a
            else:
                # set point to the beginning of the line in the middle of the window
                visible = self.view.visible_region()
                top_line = self.view.rowcol(visible.begin())[0]
                bottom_line = self.view.rowcol(visible.end())[0]
                pos = self.view.text_point((top_line + bottom_line) / 2, 0)
            self.set_selection(pos, pos)
        if ViewState.current.active_mark:
            self.toggle_active_mark_mode()

class JoveConvertPlistToJsonCommand(JoveTextCommand):
    JSON_SYNTAX = "Packages/Javascript/JSON.tmLanguage"
    PLIST_SYNTAX = "Packages/XML/XML.tmLanguage"

    def run_cmd(self, edit):
        import json
        from plistlib import readPlistFromBytes, writePlistToBytes

        data = self.view.substr(sublime.Region(0, self.view.size())).encode("utf-8")
        self.view.replace(edit, sublime.Region(0, self.view.size()),
                          json.dumps(readPlistFromBytes(data), indent=4, separators=(',', ': ')))
        self.view.set_syntax_file(JSON_SYNTAX)

class JoveConvertJsonToPlistCommand(JoveTextCommand):
    JSON_SYNTAX = "Packages/Javascript/JSON.tmLanguage"
    PLIST_SYNTAX = "Packages/XML/XML.tmLanguage"

    def run_cmd(self, edit):
        import json
        from plistlib import readPlistFromBytes, writePlistToBytes

        data = json.loads(self.view.substr(sublime.Region(0, self.view.size())))
        self.view.replace(edit, sublime.Region(0, self.view.size()), writePlistToBytes(data).decode("utf-8"))
        self.view.set_syntax_file(PLIST_SYNTAX)

def InitModule(module_name):
    def get_cmd_name(cls):
        name = cls.__name__
        name = re.sub('(?!^)([A-Z]+)', r'_\1', name).lower()
        # strip "_command"
        return name[0:len(name) - 8]

    module = sys.modules[module_name]
    for name in dir(module):
        if name.startswith("Jove"):
            cls = getattr(module, name)
            try:
                if not issubclass(cls, sublime_plugin.TextCommand):
                    continue
            except:
                continue
            # see what the deal is
            name = get_cmd_name(cls)
            cls.jove_cmd_name = name
            if cls.is_kill_cmd:
                ViewState.kill_cmds.add(name)
            if cls.is_ensure_visible_cmd:
                ViewState.ensure_visible_cmds.add(name)

InitModule(__name__)
