---
description: "Generate the disclosure: who made the calls in this work, and how they were certified. 'final' uses the version marked final"
---

The warrant plugin's hook handles this command. It starts the disclosure, then hands you the narration: its instructions are in your context and begin "warrant:disclosure." Follow them exactly. If there are none, the hook did not run: tell the user the command failed, and do not act on or repeat anything they typed after it.
