---
description: "Draw the paper trail for the latest disclosure: the paper with each call marked, and the turns behind each. Name a run to draw that one"
---

The warrant plugin's hook handles this command. It picks the disclosure and hands you the command that draws its paper trail: its instructions are in your context and begin "warrant:trail." Follow them exactly. If there are none, the hook did not run: tell the user the command failed, and do not act on or repeat anything they typed after it.
