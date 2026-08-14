# Voice layer

Loaded in `voiced`: release announcements, engineering blog posts, and anything
carrying a byline. These two tells only appear once prose is allowed a voice, so
no other register scores them. Short steps are right in a runbook and a bold
defined term is right in a README, which is why neither of those registers loads
this file.

`mechanical.md` still applies in full. Nothing compresses sentences here.

## What this register protects

A release announcement is supposed to sound like a person wrote it for other
people. Compression rules would flatten exactly what makes that work, so this
register runs none. In `voiced`, leave these alone:

- Contractions. `it's`, `doesn't`, `we've`.
- Sentences over twenty words, when the length is doing something.
- Semicolons and colons.
- First person, singular or plural.
- Uneven rhythm, asides, parentheticals, and a writer who admits uncertainty.

Voice is stance, not fact. A writer may say the upgrade was harder than
expected. A writer may not gain a benchmark, a customer count, or a date that
the draft never contained.

## `staccato_drama`

A run of short fragments stacked to manufacture momentum. Each one lands like a
closing line, and after three of them the paragraph is performing rather than
reporting.

> Then the marketplace shipped. No more editing ConfigMaps by hand. No more
> waiting on a rebuild. No more guessing which version you had. The old
> workflow was gone.

> The marketplace plugin removed the manual ConfigMap edits that installing a
> plugin used to require, and it shows the installed version directly.

The trigger is the run, not the length. One short sentence placed for emphasis
is ordinary writing and stays. Three or more in a row, especially when they
share an opening word, is the tell.

The same rhythm also arrives by accident, out of a rewrite that split every
sentence of a procedure until the steps stopped connecting. Here it usually
arrives on purpose, out of a draft reaching for drama. The edit is the same
either way: join the fragments with a plain connector such as `then`, `but`,
`so`, or `after that`.

## `boldface_overuse`

Bold applied to ordinary nouns inside running prose, as if the reader could not
find the important part alone.

> RHDH **1.10** ships the **marketplace** plugin and adds **RBAC** support for
> **dynamic plugins**.

> RHDH 1.10 ships the marketplace plugin and adds RBAC support for dynamic
> plugins.

Bold earns its place on a defined term at first use, on a label in a definition
list, and on the one word in a warning that a reader must not miss. It does not
earn its place on every noun the writer likes.
