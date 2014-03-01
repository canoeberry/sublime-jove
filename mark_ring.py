import sublime

#
# Classic emacs mark ring. Each entry in the ring is implemented with a named view region.
#
class MarkRing:
    MARK_RING_SIZE = 16

    def __init__(self, view):
        self.view = view
        self.index = 0

        # in case any left over from before
        self.view.erase_regions("jove_mark")
        for i in range(self.MARK_RING_SIZE):
            self.view.erase_regions(self.get_key(i))

    def get_key(self, index):
        return "jove_mark:" + str(index)

    #
    # Get the current mark.
    #
    def get(self):
        key = self.get_key(self.index)
        r = self.view.get_regions(key)
        if r:
            return r[0].a

    #
    # Update the display to show the current mark.
    #
    def display(self):
        # display the mark's dot
        mark = self.get()
        if mark is not None:
            mark = sublime.Region(mark, mark)
            self.view.add_regions("jove_mark", [mark], "mark", "dot", sublime.HIDDEN)

    #
    # Set the mark to pos. If index is supplied we overwrite that mark, otherwise we push to the
    # next location.
    #
    def set(self, pos, same_index=False):
        if self.get() == pos:
            # don't set another mark in the same place
            return
        if not same_index:
            self.index = (self.index + 1) % self.MARK_RING_SIZE
        self.view.add_regions(self.get_key(self.index), [sublime.Region(pos, pos)], "mark", "", sublime.HIDDEN)
        self.display()

    #
    # Exchange the current mark with the specified pos, and return the current mark.
    #
    def exchange(self, pos):
        val = self.get()
        if val is not None:
            self.set(pos, False)
            return val

    #
    # Pops the current mark from the ring and returns it. The caller sets point to that value. The
    # new mark is the previous mark on the ring.
    #
    def pop(self):
        val = self.get()

        # find a non-None mark in the ring
        start = self.index
        while True:
            self.index -= 1
            if self.index < 0:
                self.index = self.MARK_RING_SIZE - 1
            if self.get() is not None or self.index == start:
                break
        self.display()
        return val
