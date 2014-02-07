import functools as fu
import sublime
import sublime_plugin

try:
    import paragraph
except ImportError:
    import Default.paragraph as paragraph

def enum(**enums):
    return type('Enum', (), enums)

# Sublime 3 compatibility
try:
    import paragraph
except ImportError:
    import Default.paragraph as paragraph

class JoveState():
    last_cmd = None
    argument_supplied = False
    argument_value = 0

#
# here we put a bunch of useful helpers for moving around and manipulating buffers
#
class JoveTextCommand(sublime_plugin.TextCommand):
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

    def get_type_string(self, type):
        vals = []
        for bit,name in self.class_names.items():
            if (type & bit) != 0:
                vals.append(name)
        return ",".join(vals)

    # Returns point. Point is where the cursor is in the possibly extended region. If there are multiple cursors it
    # uses the first one in the list.
    #
    def get_point(self):
        sel = self.view.sel()
        return sel[0].b

    #
    # A way to run a command in the context of each of the current cursors. The end result is that all the cursors are
    # updated based on the return value from each invokation of the command.
    #
    def for_each_cursor(self, method, *args, **kwargs):
        pass

    #
    # Move 'count' words from the current position. If count > 0 move forward, otherwise backward.
    #
    def move_word(self, count, is_sexpr=False):
        view = self.view

        print(self.get_point)

        settings = view.settings()
        separators = None
        if is_sexpr:
            separators = settings.get("sexpr_separators")
        if separators is None:
             separators = settings.get("word_separators")
        selection = view.sel()
        points = [sel.a for sel in selection]
        def move_word0(point, forward, first):
            if forward:
                if not first or not self.is_word_char(point, True):
                    point = view.find_by_class(point, True, sublime.CLASS_WORD_START, separators)
                point = view.find_by_class(point, True, sublime.CLASS_WORD_END, separators)
            else:
                if not first or not self.is_word_char(point, False):
                    point = view.find_by_class(point, False, sublime.CLASS_WORD_END, separators)
                point = view.find_by_class(point, False, sublime.CLASS_WORD_START, separators)
            return point

        first = True
        forward = count > 0
        for c in range(abs(count)):
            for i in range(len(points)):
                point = points[i]
                points[i] = move_word0(points[i], forward, first)
            first = False
        selection.clear()
        for p in points:
            selection.add(sublime.Region(p, p))

    def looking_at(self, regex):
        pass

    def skip_chars(self, regex, dir):
        pass

    def is_word_char(self, pos, forward):
        if forward:
            type = self.view.classify(pos)
            return (type & (512 | sublime.CLASS_WORD_START)) != 0
        else:
            pos = pos - 1
            type = self.view.classify(pos)
            return pos >= 0 and (type & (512 | sublime.CLASS_LINE_END)) != 0

class JoveMoveWordCommand(JoveTextCommand):
    def run(self, edit, **args):
        count = 1 if args.get('forward', False) else -1
        self.move_word(count, False)

class JoveMoveSexprCommand(JoveTextCommand):
    def run(self, edit, **args):
        count = 1 if args.get('forward', False) else -1
        parens_only = args.get('parens_only', False)
        if parens_only:
            # search for parens and then skip over them
            pass

        self.move_word(count, True)

class JoveDeleteWhiteSpace(sublime_plugin.TextCommand):
    """Deletes white space around point like in emacs."""

    def run(self, edit):
        sel = self.view.sel()

        cursor_region = sel[0]
        point = cursor_region.begin()
        line = self.view.line(point)
        cur = self.view.substr(point)
        prev = self.view.substr(point - 1) if point > line.begin() else u'\x00'

        if prev.isspace():
            prefix_ws_region = self._handle_prefix_whitespace(point, line)
        else:
            prefix_ws_region = None

        if cur.isspace() and (not self._line_end(cur)):
            suffix_ws_region = self._handle_suffix_whitespace(point, line)
        else:
            suffix_ws_region = None

        if (suffix_ws_region is None) and (prefix_ws_region is None):
            # We're not on white space. Insert a blank.
            self.view.insert(edit, point, ' ')
        else:
            # Now do the actual delete.
            if suffix_ws_region is not None:
                self.view.erase(edit, suffix_ws_region)

            if prefix_ws_region is not None:
                self.view.erase(edit, prefix_ws_region)

            # Make sure there's one blank left, unless:
            #
            # a) the next character is not a letter or digit, or
            # b) the previous character is not a letter or digit, or
            # c) we're at the beginning of the line
            point = self.view.sel()[0].begin()
            bol = line.begin()
            if point > bol:
                def letter_or_digit(c):
                    return c.isdigit() or c.isalpha()

                c = self.view.substr(point)
                c_prev = self.view.substr(point - 1)

                if letter_or_digit(c) or letter_or_digit(c_prev):
                    self.view.insert(edit, point, ' ')

    def _handle_prefix_whitespace(self, point, line):
        p = point - 1
        c = self.view.substr(p)
        bol = line.begin()
        while (p > bol) and c.isspace():
            p -= 1
            c = self.view.substr(p)

        # "point" is now one character behind where we want it to be,
        # unless we're at the beginning of the line.
        if p > bol or (not c.isspace()):
            p += 1

        # Return the region of white space.
        return sublime.Region(p, point)

    def _handle_suffix_whitespace(self, point, line):
        p = point
        c = self.view.substr(p)
        eol = line.end()
        while (p <= eol) and (c.isspace()) and (not self._line_end(c)):
            p += 1
            c = self.view.substr(p)

        # Return the region of white space.
        return sublime.Region(point, p)

    def _line_end(self, c):
        return (c in ["\r", "\n", u'\x00'])


################################################################################
# Centering View
################################################################################



# All Scroll Types
SCROLL_TYPES = enum(TOP=1, CENTER=0, BOTTOM=2)

class SbpRecenterInView(sublime_plugin.TextCommand):
    '''
    Reposition the view so that the line containing the cursor is at the
    center of the viewport, if possible. Like the corresponding Emacs
    command, recenter-top-bottom, this command cycles through
    scrolling positions.

    This command is frequently bound to Ctrl-l.
    '''

    last_sel = None
    last_scroll_type = None
    last_visible_region = None


    def rowdiff(self, start, end):
        r1,c1 = self.view.rowcol(start)
        r2,c2 = self.view.rowcol(end)
        return r2 - r1


    def run(self, edit):
        start = self.view.sel()[0]
        if start != SbpRecenterInView.last_sel:
            SbpRecenterInView.last_visible_region = None
            SbpRecenterInView.last_scroll_type = SCROLL_TYPES.CENTER
            SbpRecenterInView.last_sel = start
            self.view.show_at_center(SbpRecenterInView.last_sel)
            return
        else:
            SbpRecenterInView.last_scroll_type = (SbpRecenterInView.last_scroll_type + 1) % 3

        SbpRecenterInView.last_sel = start
        if SbpRecenterInView.last_visible_region == None:
            SbpRecenterInView.last_visible_region = self.view.visible_region()

        # Now Scroll to position
        if SbpRecenterInView.last_scroll_type == SCROLL_TYPES.CENTER:
            self.view.show_at_center(SbpRecenterInView.last_sel)
        elif SbpRecenterInView.last_scroll_type == SCROLL_TYPES.TOP:
            row,col = self.view.rowcol(SbpRecenterInView.last_visible_region.end())
            diff = self.rowdiff(SbpRecenterInView.last_visible_region.begin(), SbpRecenterInView.last_sel.begin())
            self.view.show(self.view.text_point(row + diff-2, 0), False)
        elif SbpRecenterInView.last_scroll_type == SCROLL_TYPES.BOTTOM:
            row, col = self.view.rowcol(SbpRecenterInView.last_visible_region.begin())
            diff = self.rowdiff(SbpRecenterInView.last_sel.begin(), SbpRecenterInView.last_visible_region.end())
            self.view.show(self.view.text_point(row - diff+2, 0), False)
