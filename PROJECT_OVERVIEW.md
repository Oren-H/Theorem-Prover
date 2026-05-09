# Clean — Project Overview

*A minimalist, command-driven theorem prover*

---

## Table of Contents

1. [Motivation](#motivation)
2. [Usage](#usage)
3. [Architecture Overview](#architecture-overview)
4. [Comparison to Lean](#comparison-to-lean)
5. [Future Directions](#future-directions)

---

## 1. Motivation

Formal verification has long been the domain of specialists. Tools like Lean, Coq, and Isabelle are extraordinarily powerful — they can verify software, mathematics, and hardware designs with machine-checked certainty. But they come with a steep cost: you must learn a new programming language, internalize a complex type-theory framework, and navigate tooling that was clearly designed by and for logicians.

The question that drives this project is simpler and more fundamental: **what does it feel like to prove something?**

When a mathematician works on paper, they reason in steps. They write down what they know, apply a rule, and write down what they now know. The experience is linear, cumulative, and tactile — each line on the page is a small victory, a piece of certainty extracted from uncertainty. Formal provers, by contrast, tend to feel like writing a program that, if it compiles, means the proof is valid. The result is correct, but the experience of getting there can feel disconnected from mathematical intuition.

**Clean** is an attempt to rethink that experience from the ground up. The name is a deliberate play on Lean — where Lean is rich, featureful, and deeply tied to the λ-calculus, Clean is stripped down, command-based, and focused on making every step feel concrete and legible. The goal is not to compete with Lean on power. The goal is to explore what a proof system designed around the *proving experience* might look like.

Currently, Clean covers Peano Arithmetic (PA) — the foundational axiom system for natural number arithmetic. This is a well-understood, compact domain, which makes it the perfect sandbox for experimenting with proof UX. Every result can be verified by hand; every step has an intuitive meaning. As the prover matures, the domain will expand, but the design principles established here will carry forward.

The broader ambition is this: if we can make formal verification feel as natural as working on paper — or even more natural — then the barrier to entry for verified reasoning drops dramatically. That matters not just for mathematicians, but for anyone who wants to reason carefully about systems, software, or ideas.

---

## 2. Usage

### The Core Idea: Commands and Facts

Clean's interface is built around a single, powerful idea: **every proof step is a command, and every command produces a fact**.

You type a command into the terminal. Clean validates it, applies the relevant axiom or inference rule, and adds the resulting proposition to a numbered **fact list** on screen. To build a proof, you compose commands — often referencing earlier facts by number using `#N` notation. There is no ambient programming language, no type theory to recite, no syntax beyond the commands themselves.

This is the fundamental design choice that separates Clean from traditional provers. You are not writing a program. You are issuing instructions, watching a list of truths accumulate, and using those truths to derive more truths.

### Starting Clean

```bash
pip install -r requirements.txt

python main.py              # web app — opens http://127.0.0.1:5050
python main.py --repl       # plain terminal REPL
python main.py --tui        # Textual terminal UI
python main.py --test       # run built-in proof examples
```

The web app is the recommended interface. It displays the fact list alongside the command input, with autocomplete, signature hints, and clickable fact references.

### Input Notation

| Syntax | Meaning |
|--------|---------|
| `0`, `1`, `2`, … | Integer literals — automatically converted to Peano numerals |
| `0++`, `(0++)++` | Postfix successor: `0++` means "the number after 0" |
| `#N` | Reference fact N from the current session's fact list |

Commands can be nested. When you write `mp(flip(succ_not_zero(0)), ...)`, Clean evaluates the inner calls first, recording each as its own fact before proceeding to the outer call.

---

### Commands

#### Axioms

These are the foundational truths of Peano Arithmetic. They cannot be derived — they are simply asserted.

| Command | Produces | Meaning |
|---------|----------|---------|
| `succ_not_zero(n)` | `n++ ≠ 0` | The successor of any number is never zero |
| `succ_imp_eq(n, m)` | `n++ = m++ ⇒ n = m` | If two successors are equal, their predecessors are equal |
| `add_zero_eq(n)` | `n + 0 = n` | Adding zero to any number leaves it unchanged |
| `add_succ_eq(n, m)` | `n + m++ = (n + m)++` | Addition interacts with successor as expected |

#### Inference Rules

These rules derive new facts from existing ones.

| Command | Produces | Meaning |
|---------|----------|---------|
| `cont(L)` | `¬Q ⇒ ¬P` (from `P ⇒ Q`) | Contrapositive: flip and negate an implication |
| `mp(P, L)` | `Q` (from `P` and `P ⇒ Q`) | Modus ponens: apply an implication to its antecedent |
| `flip(P)` | `r = p` or `r ≠ p` | Symmetry: swap the sides of an equality or inequality |
| `rewrite(eq, target)` | Modified `target` | Substitute one occurrence of `eq.left` with `eq.right` in `target` |
| `rewrite_fwd(eq, target)` | Modified `target` | Like `rewrite`, but only in the forward direction |

#### Logical Constructors

These commands build new propositions explicitly.

| Command | Produces | Meaning |
|---------|----------|---------|
| `mk_add(t1, t2)` | `t1 + t2` (term) | Construct an addition term |
| `mk_eq(t1, t2)` | `t1 = t2` | Assert and record an equality |
| `imp_intro(P, Q)` | `P ⇒ Q` | Construct and record an implication |

#### Induction

These commands support proofs by mathematical induction over the natural numbers.

| Command | Produces | Meaning |
|---------|----------|---------|
| `forall_intro(n, P)` | `∀n. P` | Generalize a proposition over a variable |
| `induction(base, step)` | `∀n. P` | Apply the induction schema: base case + step case → universal truth |
| `inst(fa, t)` | `P[n := t]` | Instantiate a universally quantified proposition at a specific term |

---

### Sample Proofs

The following proofs build from simple one-liners to multi-step chains, showing how the fact list accumulates naturally.

---

#### Proof 1: 0++ ≠ 0

*Goal: prove that 1 (the successor of 0) is not equal to 0.*

This is the simplest possible proof — a single axiom application.

```
succ_not_zero(0)
```

**Fact list after:**
```
1.  0++ ≠ 0
```

The Peano axiom `succ_not_zero` states this directly. One command, one fact, proof complete.

---

#### Proof 2: 0 ≠ 0++

*Goal: prove that 0 is not equal to 1. Requires using symmetry.*

The axiom `succ_not_zero` gives us `0++ ≠ 0`, but we want `0 ≠ 0++`. We use `flip` to reverse the inequality.

```
succ_not_zero(0)
flip(#1)
```

**Fact list after:**
```
1.  0++ ≠ 0
2.  0 ≠ 0++
```

Fact 1 says "1 is not 0." Fact 2 says "0 is not 1." These are the same mathematical truth, just written from different perspectives. `flip` makes that symmetry explicit.

---

#### Proof 3: (0++)++ ≠ 0++

*Goal: prove that 2 is not equal to 1. Requires contrapositive and modus ponens.*

This proof introduces the full inference chain: we use `succ_imp_eq` to get an implication about injectivity, take its contrapositive, and then apply it to a fact we've already derived.

```
flip(succ_not_zero(0))
cont(succ_imp_eq(0, 0++))
mp(#1, #2)
```

**Fact list after:**
```
1.  0 ≠ 0++
2.  0 ≠ 0++ ⇒ 0++ ≠ (0++)++
3.  0++ ≠ (0++)++
```

**Unpacking the logic:**

- `succ_imp_eq(0, 0++)` produces: `0++ = (0++)++ ⇒ 0 = 0++`
  *(If the successors are equal, the predecessors are equal.)*
- `cont(...)` flips and negates it: `0 ≠ 0++ ⇒ 0++ ≠ (0++)++`
  *(Contrapositive: if the predecessors are not equal, the successors are not equal.)*
- `mp(#1, #2)` fires the implication: since we know `0 ≠ 0++` (fact 1), we derive `0++ ≠ (0++)++` (fact 3).

Each line in the fact list is a real, verified step. The proof is not just valid — it is *readable*.

---

## 3. Architecture Overview

Clean is implemented in Python and organized into a small set of focused modules. The overall structure separates concerns cleanly: the type system lives in one place, the axiom logic in another, and the user interfaces in a third. The modules are intentionally thin and composable.

```
Theorem Prover/
├── main.py                    # Entry point — dispatches to web/repl/tui/test
├── server.py                  # Flask web server and REST API
├── requirements.txt
├── templates/
│   └── index.html             # Web app HTML shell
├── static/
│   ├── app.js                 # Web app logic (autocomplete, history, UI)
│   └── style.css              # Web app styles
└── theorem_prover/
    ├── types.py               # The proposition and term type system
    ├── validation.py          # Rules for what counts as a valid term or proposition
    ├── errors.py              # Typed exceptions for clear error messages
    ├── commands.py            # All axioms and inference rules; the session state
    ├── parser.py              # Turns raw command strings into evaluated propositions
    ├── display.py             # Renders propositions as readable Unicode strings
    ├── repl.py                # Plain terminal REPL
    └── ui.py                  # Textual terminal UI
```

### The Type System

At the heart of Clean is a strict separation between two kinds of objects: **terms** and **propositions**.

Terms are arithmetic expressions — things like `0`, `0++`, or `n + m`. Propositions are logical statements — things like `n++ ≠ 0` or `P ⇒ Q`. Terms can appear inside propositions (as the sides of an equality), but propositions can never appear inside terms. This mirrors the standard distinction in formal logic between the "language of arithmetic" and the "language of logic," and Clean enforces it at every step.

Both hierarchies are implemented as frozen (immutable) data structures, which means structural equality is automatic: two propositions are the same if and only if they have the same shape.

### The Session and Fact List

Clean maintains a single global **fact list** for each session. Every command appends to it; nothing can remove from it or modify it. The fact list is the proof. When you reference `#3`, you are pointing directly into this list.

When you reset the session, the list clears and you start fresh. There is no undo — only forward progress.

### The Parser and Evaluator

When you type a command, Clean tokenizes and parses it with a recursive-descent parser. Crucially, evaluation is interleaved with parsing: when the parser encounters a nested call like `flip(succ_not_zero(0))`, it evaluates `succ_not_zero(0)` first (recording it as a fact), then evaluates `flip(...)` on the result. This means **every subexpression you write is also recorded as a fact**, not just the outermost call. You never lose intermediate steps.

### The Web Interface

The default interface is a browser-based single-page app served by Flask. The left panel shows the fact list; the right panel shows the command reference; the bottom is a terminal-style input. Key features:

- **Inline autocomplete**: As you type, a ghost completion appears inside the input itself (not a dropdown that obscures what you're reading).
- **Signature hints**: When your cursor is inside a function's argument list, a tooltip shows which parameter is active.
- **Fact click-to-insert**: Clicking any fact in the list inserts `#N` at the cursor position.
- **Command history**: Arrow keys navigate your session history; your current draft is preserved while you browse.

---

## 4. Comparison to Lean

### Two Philosophies

Lean is a **proof programming language**. Writing a proof in Lean means writing code — you define types, apply theorems as functions, and navigate a rich type-theory framework. The machine checks your program, and if it type-checks, the proof is valid. Lean is extraordinarily expressive: it can encode virtually all of modern mathematics, and it comes with a growing library (Mathlib) of thousands of verified theorems.

Clean is a **command-driven fact accumulator**. Writing a proof in Clean means issuing instructions — each instruction generates one verified proposition, and you reference those propositions by number to build further ones. There is no ambient programming language. There are no variables to declare, no types to annotate, no monad stacks to navigate. The system is intentionally limited: it knows exactly what the user can do, and it checks each step immediately.

This difference in philosophy produces dramatically different experiences.

| | Clean | Lean |
|--|-------|------|
| Mental model | "I'm adding facts to a list" | "I'm writing a program that type-checks" |
| Entry point | Commands you can memorize | A full functional programming language |
| Errors | Immediate, per-step, plain English | Often cryptic type unification failures |
| Intermediate steps | Every sub-call is recorded | Hidden inside tactic blocks |
| Learning curve | Minutes | Weeks to months |
| Power | Peano Arithmetic (for now) | All of modern mathematics |

Clean trades power for accessibility and clarity. For learning, teaching, and experimenting with proof UX, those are the right tradeoffs.

---

### Side-by-Side Proofs

The following three proofs appear in both Clean and Lean 4. Reading them in parallel illustrates the philosophical gap.

---

#### Proof A: 0++ ≠ 0

**Clean:**
```
succ_not_zero(0)
```
*Produces:* `0++ ≠ 0`

**Lean 4:**
```lean
theorem succ_ne_zero_example : Nat.succ 0 ≠ 0 :=
  Nat.succ_ne_zero 0
```

In Clean, the command name *is* the axiom, and the fact appears immediately. In Lean, you write a theorem declaration, name it, annotate the type, and then supply the proof term. The Lean version is still short — but it requires understanding what `Nat.succ` means, why types are annotated separately from values, and how theorem application works. The Clean version requires knowing one command name.

---

#### Proof B: 0 ≠ 0++ (using symmetry)

**Clean:**
```
succ_not_zero(0)
flip(#1)
```
*Produces:*
```
1.  0++ ≠ 0
2.  0 ≠ 0++
```

**Lean 4:**
```lean
theorem zero_ne_succ : 0 ≠ Nat.succ 0 :=
  Ne.symm (Nat.succ_ne_zero 0)
```

The Lean proof is a single expression: `Ne.symm` wraps the base inequality. That is elegant — but you need to know that `Ne.symm` exists, what `Ne` is, and how function application nesting works. In Clean, `flip` is the command for "swap the sides of an inequality," and you can discover it from the command list without knowing any type theory. The step-by-step recording in Clean also makes the intermediate fact (`0++ ≠ 0`) explicitly visible, which reinforces understanding.

---

#### Proof C: (0++)++ ≠ 0++ (contrapositive and modus ponens)

**Clean:**
```
flip(succ_not_zero(0))
cont(succ_imp_eq(0, 0++))
mp(#1, #2)
```
*Produces:*
```
1.  0 ≠ 0++
2.  0 ≠ 0++ ⇒ 0++ ≠ (0++)++
3.  0++ ≠ (0++)++
```

**Lean 4 (tactic style):**
```lean
theorem succ_ne_succ_succ : Nat.succ 0 ≠ Nat.succ (Nat.succ 0) := by
  intro h
  have h2 : 0 = Nat.succ 0 := Nat.succ.inj h
  exact absurd h2 (Nat.succ_ne_zero 0).symm
```

This is where the contrast sharpens. The Lean proof works by contradiction: assume the successors are equal (`intro h`), extract the predecessor equality (`Nat.succ.inj h`), and derive a contradiction (`absurd`). It is a valid proof, but it requires knowing the `intro`/`have`/`exact`/`absurd` tactic vocabulary, understanding what `.symm` does on `Ne`, and mentally simulating a local proof context.

The Clean proof follows an explicit logical chain that reads almost like prose: "I know `0 ≠ 0++`. I know that if the predecessors were equal, the successors would be equal — so contrapositively, unequal predecessors mean unequal successors. Applying that to what I know gives me the result." Each line in the fact list is a legible landmark.

Neither approach is wrong. But for a learner encountering formal logic for the first time, or for someone exploring proof structure without committing to a new programming language, Clean's model is significantly more approachable.

---

## 5. Future Directions

### The Proving Experience as a First-Class Concern

Most theorem prover research focuses on expressiveness, automation, and correctness — can the system verify more things, faster, with less effort? These are important goals. But there is a largely unexplored design space around a different question: **what should it feel like to prove something?**

The proving experience encompasses the feedback loop between the user and the system. How immediately does the system respond? How legible are its outputs? How much does the user need to hold in their head at once? How easy is it to recover from a wrong step? How natural is it to navigate the space of possible next moves?

Clean's next iterations will treat these questions with the same rigor as correctness. Planned directions include:

**Proof visualization.** The fact list is currently linear, but proofs have structure — some facts are used later, some are dead ends, some form chains of reasoning. A graphical view of the proof as a directed dependency graph would let users see the *shape* of an argument, not just its sequential steps. This could help users understand which facts matter and where a proof is going.

**Guided proof search.** Given the current fact list and a goal proposition, Clean could suggest which commands are applicable and what they would produce. This stops short of automated proof search — the user still makes decisions — but dramatically reduces the amount the user needs to memorize. The interface becomes less like a blank terminal and more like a collaborative workspace.

**Richer error messages.** When a proof step fails, the system should explain not just *what* went wrong, but *what to try instead*. If `mp` fails because the antecedents don't match, Clean could show what would be needed to make them match, or suggest which earlier facts come close.

**Proof narratives.** Every completed proof contains a logical story. Clean could auto-generate a natural-language explanation of a proof once it is complete — "We first established X using the Y axiom, then derived Z by applying contrapositive reasoning..." — bridging the gap between formal verification and human comprehension.

---

### Beyond Peano Arithmetic

Peano Arithmetic is the right starting domain for Clean, but it is not the destination. The design principles — command-based reasoning, cumulative fact lists, immediate validation, readable output — generalize to any formal system.

The path forward involves expanding Clean into a multi-domain prover while preserving what makes it distinctive:

**Propositional and predicate logic.** Adding full first-order logic primitives would allow Clean to express and verify a much wider class of arguments. This is a natural next step after PA and would introduce quantifier reasoning beyond the `∀` already present.

**Set theory.** A command interface for basic set-theoretic reasoning (membership, union, intersection, power sets) would make Clean useful for undergraduate-level discrete mathematics.

**Type theory foundations.** A longer-term direction is connecting Clean's command model to dependent type theory — the foundation of Lean and Coq. This would allow Clean to serve as a gentle on-ramp to those systems: users learn proof reasoning in Clean's accessible environment, then graduate to the full power of a type-theoretic prover when they need it.

**Domain-specific logics.** Temporal logic for reasoning about systems that evolve over time. Modal logic for reasoning about possibility and necessity. Linear logic for reasoning about resources. Each domain has natural command vocabularies that could be expressed in Clean's style.

The key design constraint throughout: **every new domain should feel as approachable as the current one.** As capabilities grow, the interface must grow with them in a way that preserves legibility and minimizes cognitive overhead. Power and accessibility should not be in opposition.

---

### Making Formal Verification More Human

The deepest ambition behind Clean is cultural as much as technical. Formal verification is currently a niche discipline. The tools are powerful but inaccessible; the learning curve is steep; the payoff feels distant for anyone not already embedded in the field.

If the proving experience can be redesigned from first principles — starting with what feels natural, what feels immediate, what feels empowering — then formal verification becomes something that more people can do. Students can verify their homework proofs. Software engineers can check their invariants. Mathematicians can explore new territory with a machine keeping score.

Clean is a small proof of concept that this redesign is possible. The axioms are real, the inference rules are sound, and the proofs it produces are genuinely valid. But the experience of building those proofs is different from anything else in the field: immediate, readable, and grounded in the simple satisfaction of watching a fact list grow.

That experience is worth building on.

---

*Clean is under active development. The current implementation covers Peano Arithmetic with induction support. Contributions, feedback, and proof experiments are welcome.*
