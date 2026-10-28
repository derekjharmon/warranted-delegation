# Try warranted delegation

*About 20 minutes for one pass, 35 for two. Optional: the demonstrations in the submission show the same thing at full scale.*

To see a pass before you try it, watch [`walkthrough.mp4`](walkthrough.mp4): steps 1 to 6 on a newly set-up Mac, 8½ minutes, no sound. The stretches where Claude is working play at 8× speed. Nothing is cut.

You do a few minutes of work with Claude Code on a small sample project, sign it, and generate its disclosure: who made each call in the work, and whether the author warranted what was handed to the tool. If you have time, do it twice, once making some calls yourself and choosing which of Claude's to stand behind, once handing everything over, and compare the two disclosures.

## Before you start

- **Claude Code**, signed in to a Claude subscription. To install it, see [Claude Code's setup page](https://code.claude.com/docs/en/setup). No API key is needed: the disclosure runs through your subscription.
- **git** and **Python 3**. A new Mac doesn't have them until Apple's command-line tools are installed (below).
- **A note on GitHub:** if you're logged in to GitHub's command-line tool (`gh`), setup creates a private GitHub repository for the sample, because sharing the work and its record with coauthors is part of the tool. If you'd rather it didn't, log out of `gh` first, or delete the repository afterward (step 8).
- **What's sent where:** Claude Code sends your prompts and the sample to Anthropic, as it always does. The disclosure sends the sample's finished work and its record the same way, through your subscription. Nothing else leaves your computer.

If your Mac doesn't have git and Python 3, or you're not sure, run this in Terminal first and click Install. It takes 5 to 15 minutes.

```
xcode-select --install
```

Codex and Gemini: steps for these come later; for now the guide uses Claude Code.

## 1. Install the plugin from this copy

In Terminal, go to this copy's folder. If you unzipped it on your Desktop:

```
cd ~/Desktop/warrant-review-copy
```

(Or type `cd `, with a space, and drag the folder from Finder into the Terminal window. That types its path for you.) Then:

```
claude plugin marketplace add ./
claude plugin install warrant@warranted-delegation
```

Each command ends with a line starting ✔ Successfully.

## 2. Copy the sample

From the same folder:

```
cp -R reviewer/sample ~/warrant-sample-a
```

It prints nothing when it works. The sample has three files: `notes.md` (the plan, written quickly), `codebook.md`, and `teams.csv`, 40 made-up teams. The notes contain a few mistakes, as real notes do. They're listed at the end of this guide; try not to look first.

## 3. Start Claude Code and set up

```
cd ~/warrant-sample-a
claude
```

Then, in Claude Code, type:

```
/warrant:setup
```

It makes a git repository and the record, then asks you two questions: which tool you use (Claude Code) and whether the record keeps Claude's memory notes (either answer is fine). From here on, everything you and Claude do in this folder is recorded.

If git doesn't know your name and email yet, setup asks for them. Type this, with your own name and email:

```
/warrant:setup Your Name <you@example.com>
```

If you don't use GitHub's `gh`, setup says there's no online copy yet. You can ignore that.

When setup is done, make your first save. It records the sample's files as yours, before any work:

```
/warrant:attest
```

## 4. Do the work, knowing what each prompt does

The disclosure has two rows. **Judgment calls** are the decisions in the work that could have gone another way. For each one, it reports who made it, and if it was handed to the tool, whether you warranted it. **Verifiable claims** are facts a source can settle. For each one, it reports only whether it was checked, and by whom.

Each prompt below is one kind of act the disclosure reports. Type them into Claude Code one at a time, and read each answer before the next.

**1. Verification.** Type this:

```
Read notes.md and codebook.md, and check what the notes say about the data against teams.csv and the codebook. Show me every difference. Then check the Bloom et al. reference against its DOI.
```

Claude checks what the notes say against the data, the codebook, and the reference's record. A check isn't kept or handed over. The row asks only whether it happened, and who ran it.

**2. Judgment calls you make.** Type this:

```
Drop any team with an impossible value, and tell me which. Then compute the Pearson correlation between remote_share and tasks_completed, and a regression of tasks_completed on remote_share and team_size.
```

You chose the rule, the test, and the model. They show as calls you made. If Python's numpy isn't installed, Claude may do the math in plain Python. That's fine.

**3. Judgment calls you delegate.** Type this:

```
Write the result as one paragraph in memo.md, citing Bloom et al., and list every decision you made that I didn't specify.
```

Whatever Claude decides in writing the memo, you've handed over, and its list tells you which calls those are. They show as calls handed to the tool.

**4. You warrant, or not.** Open the memo in a second Terminal window and read it:

```
open -e ~/warrant-sample-a/memo.md
```

Then answer Claude's list in one prompt of your own. For each item, you can:

- change it, which shows as **you changed it**;
- keep it with a reason, which shows as **you accepted it, with a reason**;
- just say "keep", which shows as **you accepted it**;
- leave it out of your answer entirely, which shows as **you ignored it**.

Answer each however you'd like, and write down what you did with each item. That's your answer key for step 6.

## 5. Sign it

Signing saves the work and its record, signed by you. It doesn't warrant any calls; you did that in step 4.

If you checked something yourself that the record can't see, add a sentence saying so, such as a number you compared by eye with Claude's output, or a reference you looked up in your browser. The sentence counts only for the claims it names, which then show as **You checked it against the source**. Name only what you actually checked. For example:

```
/warrant:attest I compared the memo's correlation with Claude's output.
```

If you checked nothing yourself, sign with no sentence:

```
/warrant:attest
```

## 6. Generate the disclosure

Type:

```
/warrant:disclosure
```

The first time, Claude asks whether the disclosure should reach Claude through your subscription or an API key; choose your subscription. Then Claude says what it takes the finished work to be (the kind of paper, and the memo, the data, and the code) and asks whether that's right; answer in plain words, and it saves your changes in `provenance/finished-work.md` for you. Before anything is sent, Claude says what goes where and asks you to agree. Claude then narrates the run, step by step. It takes a few minutes.

Open the disclosure in a browser, from a second Terminal window:

```
open ~/warrant-sample-a/disclosure/*/disclosure.html
```

Look at:

- **Judgment calls:** how many calls you made, how many were handed to the tool, and whether you changed or accepted those.
- **Verifiable claims:** how many were checked, and by whom.
- **Calls and claims by research stage:** where in the work your calls and claims fell.

Then type:

```
/warrant:trail
```

and open the trail beside it: the memo with each call marked, and the turns behind each one when you click it.

```
open ~/warrant-sample-a/disclosure/*/trail.html
```

Now check it against what you did:

- The calls you set in prompt 2 show as **You made the call**.
- Each item on Claude's list shows under **Handed to the tool**, shaded by your answer. These should match your notes one for one.
- Calls Claude made but never mentioned show as **you were never told**. These are calls you handed over without knowing it.
- The checks Claude ran in prompt 1 show as **The tool checked it**, and say whether you confirmed reading the result.
- Any claim your sentence names shows as **You checked it against the source**.
- The memo's numbers show as **No check**, unless you checked them yourself and said so when you signed.

In the trail, click any call to see the turn it rests on, including your answer.

## 7. Optional: the second pass, you delegate everything and warrant nothing

This pass works the same sample the other way: you hand Claude every call, ask for no checks, and answer nothing.

In a new Terminal window, go to this copy's folder again, as in step 1, then:

```
cp -R reviewer/sample ~/warrant-sample-b
cd ~/warrant-sample-b
claude
```

Then, in Claude Code, type:

```
/warrant:setup
```

When setup is done, make your first save, as in step 3:

```
/warrant:attest
```

**1. Judgment calls you delegate.** Type this:

```
Using notes.md and teams.csv, write a one-paragraph finding in memo.md. Use your judgment on everything.
```

Every call in the memo is now Claude's. You asked for no checks, so any check Claude runs is its own.

**2. You don't warrant.** Don't answer anything Claude says. Go straight to signing.

**3. Sign it with no sentence**, since you checked nothing yourself:

```
/warrant:attest
```

Then generate the disclosure and the trail, letting each finish before the next:

```
/warrant:disclosure
```

```
/warrant:trail
```

Open both from a second Terminal window:

```
open ~/warrant-sample-b/disclosure/*/disclosure.html
open ~/warrant-sample-b/disclosure/*/trail.html
```

Now check it against what you did:

- Nearly every call shows under **Handed to the tool**, and none as changed or accepted by you.
- Calls Claude mentioned in its reply show as **you ignored it**, since you never answered. Calls it never mentioned show as **you were never told**.
- Checks Claude ran on its own show as **The tool checked it, and you didn't see the result**. The other claims show as **No check** or **You were never told**.
- No claim shows as checked by you.

Compare the two disclosures. The memos may read much alike, since Claude may fix the same mistakes either way. The difference is in who made the calls and who stands behind them.

## 8. Clean up

Delete the folders and remove the plugin:

```
rm -rf ~/warrant-sample-a ~/warrant-sample-b
claude plugin uninstall warrant@warranted-delegation
claude plugin marketplace remove warranted-delegation
```

If setup made GitHub repositories, they're named after the folders (`warrant-sample-a`, `warrant-sample-b`); delete them on GitHub, or with `gh repo delete warrant-sample-a`.

## What the notes got wrong

Four mistakes were planted, as an author's quick notes might have them:

1. The notes say 50 teams; the data have 40.
2. The notes say tasks are counted per month; the codebook says per quarter.
3. Team T17's `remote_share` is 1.4, which is impossible for a share.
4. The notes date Bloom, Liang, Roberts, and Ying to 2013 (their working paper's year); the article is 2015, Quarterly Journal of Economics 130(1), 165–218.

Whether each was caught, and by whom, shows in the disclosure's claims and in the trail.
