# This is SublimeJove

This is my attempt at bringing some of the basic emacs functionality Sublime Text. Other attempts have been great, and I
have borrowed from Sublemacspro as my initiation into how to write plugins in Sublime Text. I have been using emacs for
over 30 years and in my youth I implemented a popular emacs called JOVE - Jonathan's Own Version of Emacs. That is where
this plugin got its name.

## Installation

This is not in Package Control yet. Just put this folder in your Packages directory for now.

## Sublime Text 2 or 3?

This has been developed using Sublime Text 3. I don't know if it works in verison 2. I think I am using some Python APIs
that are for Python 3 and that might be a show-stopper for Sublime 2, at least for now.

## Features

    * Emacs universal argument: Control-U, Meta-0 ... Meta-9. You provide a prefix arguments to commands and the command
      is run that many times. E.g., Meta-23 Control-F means go forward 23 characters.
    * Forward and backward words with the same exact behavior of emacs.
    * Forward and backward s-expressions, sort of. It works on indentifiers but not quotes or parentheses yet.
    * Full emacs kill-ring support:
        * 64 entries
        * adjustent kill commands are appended to the same entry
        * yank and yank-pop
    * Delete word forward and backward, placinging the deleted text on the kill ring.
    * Kill to end of line: if the line only has characters on it, the newline is killed as well. Numeric
      argument to kill-line causes that many lines to be killed.
    * Kill region and copy region (ctrl+w and meta+w)
    * Support for a single emacs-style mark. I have not yet implemented the mark-ring and I am not 100% sure I will,
      since Sublime has some similar notions built-in that I am still getting used to. Various commands set the mark,
      such as yank, moving to beginning/ending of file, etc.
    * Open line with ctrl+o.
    * Goto line via numeric argument, e.g., Meta-435 Meta-g goes to line 435.
    * Center current line in view. With numeric argument, put the current line at the Nth line on the screen.
    * Delete white space around point on current line.
    * I assume origami is installed, which is a package for splitting windows ala emacs. It's not right but an OK start.
    * Activate mark. If you type ctrl+space twice in a row, it activates the mark, highlighting the region. If you already have a region and want to highlight it you can use ctrl+u ctrl+space ctrl+space, or ctrl+u ctrl+x ctrl+x. If you use the mouse to make a selection, it will set the mark and it will become the emacs region.
    * The yank command will pull from the clipboard if it finds it is not the same as the current kill-ring entry. Also, anything you kill in emacs will be placed on the clipboard for other apps.

## Multiple Cursors

Where possible I tried to make JOVE commands compatible with multiple cursors. So if there are multiple cursors active
it is possible to use the motion commands (word, s-expression, characters) as well as the delete word, etc. commands. It
is not currently possible to run the kill-line command on multiple cursors, but that might just be an oversight. And you
cannot yank into multiple cursors. For those things I find undo to be the best bet.

## Philosophy

It is my goal to embrace all that it fantastic about Sublime and not try to re-implement emacs in Sublime. But the truth
of the matter is, there are many basics that emacs got exactly right and they are worth copying. I intend to continue to
improve some of those basics while adopting as many Sublime approaches as possible.

I will continue to work on this until I am happy with it. I am currently being emacs-level productive and am already
happy with it.

### Author
Jonathan Payne (@canoeberry)
