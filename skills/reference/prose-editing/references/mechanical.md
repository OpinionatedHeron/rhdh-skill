# Mechanical layer

Loaded in every register. These are the machine tells, and they are wrong
everywhere: in a Konflux runbook, in a plugin README, in an RHIDP issue
description, and in a release blog post. Nothing here depends on how much
compression the register applies, so the edit is the same in all four routes.

## Punctuation and decoration

| Category | The tell | The edit |
|---|---|---|
| `em_dash` | `—` or `–` doing the work of a period, a comma, or a colon | a period first, a comma second, parentheses last. Catch spaced ` -- ` too. |
| `curly_quote` | `“ ” ‘ ’` left behind by a word processor | straight `"` and `'`. Never inside a code span or a shell string, where the byte matters. |
| `emoji` | a rocket, a check mark, or a warning sign decorating a heading or a bullet | delete it. The heading already carries the meaning. |
| `title_case_heading` | `## Installing Dynamic Plugins On OpenShift` | sentence case: `## Installing dynamic plugins on OpenShift`. Proper nouns keep their capitals: OpenShift, Backstage, Red Hat Developer Hub, Konflux. |

A heading that is a literal identifier stays exactly as written. `## app-config.yaml`
is a filename, not a title.

### `inline_header_list`

A bulleted list where each item opens with a bolded generic label, a colon,
then a sentence restating the label. The label carries no information and the
sentence carries almost none.

> - **Performance:** Performance has been improved in this release.
> - **Security:** Security has been strengthened for plugin loading.
> - **Usability:** The user experience of the header is now better.

Fix it by moving the fact into the item, not by deleting the list.

> - The backend starts in half the time it took in 1.9.
> - The backend verifies a dynamic plugin's integrity hash before it loads it.
> - The global-header plugin reads its layout from `app-config.yaml`.

A real term followed by its definition is a definition list, and it is fine.
`**RHIDP**: the Jira project for Developer Hub engineering work` is not this
tell.

## Chatbot residue and hedging

### `chatbot_residue`

Conversation with the assistant, pasted into the document as if it were
content. Delete the whole sentence and keep what surrounded it.

> Here is an overview of the bulk-import plugin. I hope this helps! Let me know
> if you would like the API reference as well.

> The bulk-import plugin adds repositories from a GitHub organization to the
> software catalog.

### `modal_hedge`

A sentence that announces the importance of the next clause instead of stating
it. Delete the announcement and keep the clause.

> It is important to note that the operator does not restart the Deployment on
> every reconcile.

> The operator does not restart the Deployment on every reconcile.

The same edit applies to `it should be noted`, `it is worth noting`, `please
note that`, `as mentioned above`, and `as previously discussed`.

### `filler_phrase`

| Do not write | Write |
|---|---|
| due to the fact that | because |
| at this point in time | now |
| in the event that | if |
| has the ability to | can |
| a number of | the count from the source, or `some` |
| for the purpose of | to |

### `vague_attribution`

A claim credited to an authority that is never named.

> Industry reports show that platform teams prefer a single developer portal.

Name the source when the draft has one, and cut the sentence when it does not.

## Inflation

### `ai_vocabulary`

Words that are wrong in every register. A word that is merely long is a
compression problem rather than a machine tell, so it is not listed here.

| Do not write | Write |
|---|---|
| leverage, utilize | use |
| delve into | read, examine |
| crucial, pivotal, vital | say what breaks without it, or cut |
| seamless, effortless | cut |
| robust, powerful, cutting-edge | cut, or keep a measure the source already gives |
| showcase | show, list |
| underscore, highlight (as a verb) | say the point directly |
| landscape, tapestry, ecosystem (as abstract nouns) | name the actual set of things |
| testament to | cut |
| align with | match, follow |
| intricate, nuanced | cut, or say what the complication is |

> The marketplace plugin leverages a robust catalog to showcase the plugin
> landscape.

> The marketplace plugin reads the catalog and lists the available plugins.

### `promotional`

Advertisement register in a document nobody is buying.

| Do not write | Write |
|---|---|
| boasts a, features a | has |
| vibrant, thriving, rich | cut |
| nestled in, at the heart of | the actual location, or cut |
| renowned, industry-leading, best-in-class | cut |
| breathtaking, stunning | cut |
| commitment to, dedication to | the thing that was actually done |

> Red Hat Developer Hub boasts a vibrant plugin ecosystem and a deep commitment
> to developer productivity.

> Red Hat Developer Hub supports dynamic plugins.

### `authority_trope`

A ceremonial run-up that promises a deeper truth and then delivers an ordinary
point. Watch for `the real question is`, `at its core`, `what really matters`,
`fundamentally`, `the deeper issue`.

> At its core, what really matters about dynamic plugins is load order.

> Dynamic plugins depend on load order.

### `aphorism`

An ordinary claim reshaped into a portable saying. Watch for `X is the Y of Z`,
`the currency of`, `the architecture of`, `X becomes a trap`.

> Configuration is the tax you pay for flexibility.

> Every option in `app-config.yaml` is one more thing to keep working.

### `generic_conclusion`

A closing paragraph made of good feeling and no content. The usual shapes are a
bright future, an invitation to build something, and a thank-you to a community
that was never described. A `## Conclusion` heading over one of them counts too.

> The future of the platform is bright, and we cannot wait to see what you
> build with it. Exciting things are ahead.

> In conclusion, the possibilities with dynamic plugins are endless.

The second one is the reason this sits in the mechanical layer: a README ends
that way as readily as an announcement does.

Delete the paragraph and stop wherever the draft last said something specific:
the release date, the upgrade path, the docs link, the tracker that takes
feedback. When the draft states real plans, use those. Rewriting one send-off
into a better send-off leaves the same defect in place.

### `significance_inflation`

A sentence whose only job is to say that the topic matters. It usually claims a
turning point, a broader trend, or an ongoing commitment.

> The 1.10 release marks a pivotal moment in the evolution of the platform and
> underscores our ongoing commitment to the developer community.

> Red Hat Developer Hub 1.10 is generally available today.

Watch for `marks a turning point`, `represents a shift`, `reflects a broader`,
`sets the stage for`, `is a testament to`, `plays a key role in`, `leaves an
indelible mark`.

The test is subtraction. Delete the sentence and read the paragraph again. When
nothing factual is missing, the sentence was inflation. When the draft has a
real reason the release matters, such as a deprecation deadline or a supported
upgrade path, state that reason instead of the feeling.

| Do not write | Write |
|---|---|
| a pivotal moment in the evolution of | what changed |
| reflects a broader shift toward | the change itself, when the draft names one |
| underscores our commitment to | what was shipped |
| sets the stage for | what happens next, with its date, when the draft has one |

## Sentence shapes

### `copula_avoidance`

An elaborate verb standing in for `is` or `has`.

> The dynamic-plugins ConfigMap serves as the source of truth for enabled
> plugins.

> The dynamic-plugins ConfigMap lists the enabled plugins.

`serves as`, `stands as`, `represents`, `marks`, and `boasts` all collapse to
`is` or `has`, or to a verb that names the real job.

### `negative_parallelism`

Three shapes, one habit: defining a thing by what it is not.

> It is not just a plugin registry, it is a marketplace.

> The marketplace plugin lists plugins and installs them.

> Not only does the operator create the Deployment, it also creates the Route.

> The operator creates the Deployment and the Route.

The third shape is a negation fragment tacked onto a sentence in place of a
real clause.

> The overlay reads the version from the plugin's `package.json`, no manual
> bumps.

> The overlay reads the version from the plugin's `package.json`, so nobody
> edits it by hand.

### `ing_analysis`

A trailing participial phrase bolted onto a finished sentence to add depth it
does not have. Split it into its own sentence when it carries a fact, and cut
it when it does not.

> The operator now watches the ConfigMap, ensuring that the backend restarts
> whenever the configuration changes and reflecting a tighter reconcile loop.

> The operator watches the ConfigMap. The backend restarts when the
> configuration changes.

Watch for a comma followed by `highlighting`, `underscoring`, `ensuring`,
`reflecting`, `contributing to`, `showcasing`, `enabling`, `allowing`.

### `false_range`

A `from X to Y` frame whose endpoints do not sit on a scale.

> The plugin catalog covers everything from authentication to observability,
> from CI status to cost insights.

> The plugin catalog includes authentication, observability, CI status, and
> cost plugins.

### `signposting`

Announcing the next paragraph instead of writing it. Watch for `let us dive
in`, `here is what you need to know`, `now let us look at`, `in this section we
will`.

> Let us look at how the operator mounts the ConfigMap. Here is what you need
> to know.

> The operator mounts the app-config ConfigMap into the backend container.

A heading already does this job, which is why the sentence under it is
redundant.

### `rhetorical_opener`

A staged pause before an ordinary answer. Watch for a standalone `Honestly?`,
`Look,`, `Here is the thing`, `The thing is`, `Let us be honest`.

> Is the 1.10 upgrade safe? Honestly? It depends on which dynamic plugins you
> enabled.

> Whether the 1.10 upgrade is safe depends on which dynamic plugins you
> enabled.

The word inside a sentence is ordinary English. The tell is the theatrical
one-word opener.

## Markers

Reported in `markers`, never added to the score. Fix them anyway when the fix
is cheap, and never let them drive a rewrite on their own.

### `noun_train`

Four or more nouns stacked with nothing between them. Keep a multi-word noun to
three words at most. Unpack the rest with `of`, `that`, or a hyphen.

> the dynamic plugin registry cache invalidation handler

> the handler that invalidates the dynamic-plugin registry cache

A product name is one noun no matter how many words it holds. Red Hat Developer
Hub is not a noun train.

### `rule_of_three`

Three abstract nouns in a row, arranged for rhythm rather than for content.

> The 1.10 release brings speed, stability, and simplicity.

> The 1.10 release cuts backend startup time and adds RBAC for dynamic plugins.

A list with three real members is a fact, not a tell. Three supported OpenShift
versions, three Jira projects, and three failing tasks in a PipelineRun all
stay as they are.
