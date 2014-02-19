# This is Sublime Jove

This is a plugin for Sublime Text 3.

This is my attempt at bringing some of the basic emacs functionality to Sublime Text. Other attempts have been great but
they weren't quite right so I decided to try my own. Along the way I have learned an awful lot from reading the
Sublemacspro plugin and in some places I have stolen mercilessly from their ideas.

I have been using emacs for over 35 years and in my youth I implemented a version of emacs called JOVE -
Jonathan's Own Version of Emacs. That is where this plugin got its name.

## Installation

This is not in Package Control yet. Just put this folder in your Packages directory for now.

## Sublime Text 2 or 3?

This has been developed using Sublime Text 3. I don't know if it works in verison 2. I think I am using some Python APIs
that are for Python 3 and that might be a show-stopper for Sublime 2, at least for now. I will investigate more later.

## Features

Here are the main set of commands I have implemented or adjusted to conform to proper emacs behavior.

   * ``C-u``, ``M-0`` ... ``M-9``: Emacs universal argument - you provide a prefix arguments to a command to run it that many times. E.g., ``M-2`` M-3`` ``C-F`` means go forward 23 characters.
   * ``M-f`` and ``M-b``: Forward and backward words with the same exact behavior of emacs in terms of how you move.
   * ``C-M-f`` and ``C-M-b``: Forward and backward s-expressions. Initially it works on indentifiers but not quotes or parentheses yet.
   * Full emacs kill ring support:
     * 64 entries - not currently adjustable
     * adjascent kill commands are appended to the same entry
     * ``C-w`` and ``M-w``: kill and copy to the kill ring.
     * ``C-y`` and ``M-y``: yank and yank-pop.
     * technically supplying a numeric argument to ``C-d`` and ``C-backspace`` should append to the kill ring but I have not done that (yet).
     * The yank command will pull from the clipboard if it finds it is not the same as the current kill-ring entry, meaning you can go into a different app and copy something there and paste it into emacs using ``C-y``. Also, anything you kill in emacs will be placed on the clipboard for other apps to access.
   * ``M-d`` and ``M-backspace``: Delete word forward and backward, placinging the deleted text on the kill ring.
   * ``C-k``: Kill to end of line mimics emacs almost exactly (it does not support a 0 numeric argument to delete to the beginning of the line). Providing a numeric argument means "delete that many lines" which is different from typing ``C-k`` that many times.
   * ``M-<`` and ``M->``: move to beginning and end of file.
   * ``M-,`` and ``M-.``: move to beginning and end of window.
   * ``C-space`` and ``C-x C-x``: Support for a single emacs-style mark.
     * I have not yet implemented the mark-ring but I probably will despite there being similar functionality in Sublime.
     * Various commands set the mark, such as ``C-y``, ``M-y`` as they do (and must) in emacs. ``M-<`` and ``M->`` also set the mark as do ``M-,`` and ``M-.``.
     * If you type ``C-space`` twice in a row, it will activate the mark, which means "highlight it as a selection". It stays highlighted until you type ``C-g`` or execute certain commands.
     * If you supply a numeric argument, e.g., ``C-u C-x C-x`` or ``C-u C-space``, it will activate the mark without moving the cursor.
     * If you use the mouse to make a selection, it will set the mark and it will become the emacs region as well.
   * ``C-o``: Open line.
   * ``M-g``: Goto line via numeric argument, e.g., ``M-4 M-3 M-5 Meta-g`` goes to line 435. (Meta-g is not a great choice on Mac OS.)
   * ``C-l``: Center current line in view. With numeric argument, put the current line at the Nth line on the screen.
   * ``M-backslash``: Delete white space around point.
   * ``C-x 1``, ``C-x 2``, ``C-x-o``: Split and join windows. I assume the Origami package is installed, which is a package for splitting windows ala emacs. It's not right but an OK start.
   * ``C-s`` and ``C-r``: proper emacs-style incremental search
     * As you type the search string grows and all the matches are highlighted.
     * If you type ``C-s`` again you will move to the next match.
     * If you type ``Backspace`` you are restored you to your previous search state. It will go back to a previous match or delete a character from your search string.
     * If you type ``C-w`` while searching, the characters from your buffer are appended to your search string.
     * If your search is currently failing, you can type ``C-g`` to go back to the last point your search was succeeding. If you type ``C-g`` when your search is succeeding, the search is aborted.
     * Clicking the mouse will abort the search, as will opening an overlay.
     * You can quit your search by typing many regular emacs commands, e.g., C-a, M-f, C-l, M-<, M->.
     * When you complete a search your mark is set to where you started from.
   * Sublime Incremental Search extensions:
     * If you type ``C-d`` while search (CMD-d) your current match is added to the future cursor and you move to the next match.
     * If you change your mind about a ``C-d``, you can press ``Backspace`` to undo it.
     * This allows you to selectively pick which matches you want to add to your cursors, as well as allowing you to undo a mistake if you accidentally select one too many.

## Multiple Cursors

Where possible I tried to make JOVE commands compatible with multiple cursors. So if there are multiple cursors active
it is possible to use the motion commands (word, s-expression, characters) as well as the delete word, etc. commands. It
is not currently possible to run the kill-line command on multiple cursors, but that might just be an oversight. And you
cannot yank into multiple cursors. That should be possible but isn't always what you want or expcet. Often ``undo`` is
the best approach for these things.

## Philosophy

It is my goal to embrace all that is fantastic about Sublime Text and not try to re-implement emacs in Sublime. But the
truth of the matter is, there are many basic things that emacs got exactly right 40 years ago and they are worth
preserving. I intend to continue to improve some of those basics while adopting as many Sublime approaches as possible.

### Author
Jonathan Payne (@canoeberry)
