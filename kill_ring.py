import sublime

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
