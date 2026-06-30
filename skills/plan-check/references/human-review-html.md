# Human Review HTML

This file defines the required shape when `$plan-check` outputs or writes
`Human Review HTML`. Read it before writing the final fenced `html` block and
the default preview file at `plan-check-codex/human-review.html`.

## Core Rules

- Match the user's language for all visible labels and prose. In Chinese
  conversations, use Chinese-first labels such as `计划审核结果`, `审核结论`,
  `严重级别汇总`, `Program 汇总`, `Program 验收闭环`, `发现的问题`,
  `待确认问题`, `建议下一步`, and `人工批准清单`.
- Preserve technical identifiers, commands, file names, API names, status names,
  and quoted text exactly.
- The HTML must be self-contained: no external CSS, assets, JavaScript,
  tracking, generated timestamps, or live links.
- Inline CSS is allowed for layout, borders, chips, and status colors. Keep it
  readable as one compact page.
- Do not include real file paths, long command logs, evidence catalogs, source
  labels, or internal scratch notes in the checklist.
- The HTML must reflect the same verdict, severity counts, findings, open
  questions, recommended next step, and approval readiness as the text review.
- The default file is a fixed local preview artifact:
  `plan-check-codex/human-review.html`. It is overwritten on each review, must
  stay out of git, and must not be used as a hook gate or approval record.

## Structure

When emitted, every HTML review must contain these sections:

1. Result header: title, short subtitle, verdict badge, severity summary, and
   plan metadata.
2. Execution-unit detail:
   - plain plan: render each milestone or task as a reviewable unit;
   - roadmap: render each Version as a card;
   - program: render each child Roadmap as a card and expand every Version under
     that child Roadmap.
3. Findings.
4. Open Questions.
5. Recommended Next Step.
6. Approval Checklist.

For Program reviews, the `Program 验收闭环` section is mandatory. It must not stop
at Roadmap-level summaries. It must expand each child Roadmap down to Version
level so the human reviewer can see whether every independently reviewable unit
has concrete acceptance.

## Version Cards

Each roadmap or program Version card must include:

- Version identifier.
- Status chip when known.
- `完成标准`: the unit-specific done condition.
- `硬指标`: measurable acceptance metric, threshold, pass count, or observable
  target. Prefer hard numbers or binary pass/fail criteria.
- `证据`: the verification result or evidence summary that proves the unit met
  the hard metric.

If the plan has overall program acceptance or final integration proof, render it
as a final proof card or final program item, not as a vague note.

## Approval Readiness

- Checkbox inputs appear only for `PASS` or `CONCERNS` with `P2` findings only.
- If any `P0` or `P1` exists, do not output checkbox inputs. The checklist
  section must say the user's-language equivalent of `Not ready for human
  approval until P0/P1 findings are resolved.` In Chinese, use `P0/P1 问题解决前，不可进入人工批准。`
- Use one checklist item per independently reviewable execution unit. For a
  Program, include child Roadmap or Version-level approval items plus a final
  Program acceptance item when the program has overall acceptance criteria.
- Derive checklist text from `Done when` and hard acceptance conditions.
- Keep checklist text short enough for direct human approval.

## Chinese Program Skeleton

Use this approved shape for Chinese Program reviews and adapt the contents to
the actual plan:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>计划审核结果</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f6f8;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #5f6875;
      --line: #d9dee6;
      --pass: #137333;
      --warn: #9a6700;
      --block: #b3261e;
      --chip: #eef3fb;
      --soft: #f9fafc;
      --accent: #244e8f;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    main {
      max-width: 1040px;
      margin: 0 auto;
      padding: 32px 20px 44px;
    }
    h1 {
      margin: 0 0 6px;
      font-size: 28px;
      letter-spacing: 0;
    }
    .subtitle {
      margin: 0 0 18px;
      color: var(--muted);
      line-height: 1.45;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 17px;
      letter-spacing: 0;
    }
    h3 {
      margin: 0;
      font-size: 15px;
      letter-spacing: 0;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin-top: 14px;
    }
    .verdict {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 6px 12px;
      border-radius: 999px;
      color: #fff;
      background: var(--pass);
      font-weight: 700;
    }
    .badge.concerns { background: var(--warn); }
    .badge.blocked { background: var(--block); }
    .meta, .severity {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    .meta span, .severity span, .status-chip {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 10px;
      background: #fff;
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }
    .status-chip.done {
      color: var(--pass);
      border-color: #b7d8c2;
      background: #eef8f0;
      font-weight: 700;
    }
    .roadmap {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
      padding: 14px;
      margin-top: 12px;
    }
    .roadmap-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: start;
      margin-bottom: 12px;
    }
    .roadmap-head p {
      margin: 6px 0 0;
      color: var(--muted);
      line-height: 1.42;
    }
    .version-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .version {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fff;
    }
    .version-title {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: start;
      margin-bottom: 8px;
    }
    .version p {
      margin: 7px 0;
      color: var(--muted);
      line-height: 1.45;
    }
    ul { margin: 0; padding-left: 20px; }
    li { margin: 8px 0; line-height: 1.48; }
    .empty { color: var(--muted); }
    .checklist { list-style: none; padding-left: 0; }
    .checklist li {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      background: #fbfcfe;
    }
    label {
      display: flex;
      gap: 10px;
      align-items: flex-start;
    }
    input {
      width: 18px;
      height: 18px;
      margin-top: 2px;
      accent-color: var(--pass);
    }
    code {
      border: 1px solid var(--line);
      border-radius: 4px;
      padding: 1px 5px;
      background: var(--chip);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.92em;
    }
    .final-proof {
      border-left: 4px solid var(--accent);
      background: #f7faff;
    }
    @media (max-width: 760px) {
      main { padding: 22px 14px 34px; }
      .verdict, .roadmap-head, .version-grid { grid-template-columns: 1fr; }
      .badge { width: fit-content; }
      .version-title { display: block; }
      .version-title .status-chip { display: inline-flex; margin-top: 8px; }
    }
  </style>
</head>
<body>
  <main>
    <h1>计划审核结果</h1>
    <p class="subtitle">&lt;计划类型&gt;：<code>&lt;plan-id&gt;</code></p>

    <section class="verdict" aria-label="审核结论">
      <div>
        <h2>审核结论</h2>
        <p><strong>结果：</strong>PASS | CONCERNS | BLOCKED</p>
        <div class="severity" aria-label="严重级别汇总">
          <span>P0=&lt;count&gt;</span>
          <span>P1=&lt;count&gt;</span>
          <span>P2=&lt;count&gt;</span>
        </div>
        <div class="meta" aria-label="Program 汇总">
          <span>&lt;program status&gt;</span>
          <span>&lt;roadmap count&gt; 个 Roadmap</span>
          <span>&lt;version count&gt; 个 Version</span>
          <span>&lt;final proof status&gt;</span>
        </div>
      </div>
      <div class="badge">PASS</div>
    </section>

    <section aria-label="Program 验收闭环">
      <h2>Program 验收闭环</h2>

      <article class="roadmap">
        <div class="roadmap-head">
          <div>
            <h3>&lt;roadmap-id&gt;</h3>
            <p>目标：&lt;roadmap goal&gt;</p>
          </div>
          <span class="status-chip done">&lt;status&gt;</span>
        </div>
        <div class="version-grid">
          <div class="version">
            <div class="version-title">
              <h3>&lt;version-id&gt;</h3>
              <span class="status-chip done">&lt;status&gt;</span>
            </div>
            <p><strong>完成标准：</strong>&lt;unit done condition&gt;</p>
            <p><strong>硬指标：</strong>&lt;measurable acceptance metric&gt;</p>
            <p><strong>证据：</strong>&lt;verification evidence summary&gt;</p>
          </div>
          <div class="version final-proof">
            <div class="version-title">
              <h3>&lt;final-proof-id&gt;</h3>
              <span class="status-chip done">&lt;status&gt;</span>
            </div>
            <p><strong>完成标准：</strong>&lt;program-level done condition&gt;</p>
            <p><strong>硬指标：</strong>&lt;program-level hard metric&gt;</p>
            <p><strong>证据：</strong>&lt;final integration proof&gt;</p>
          </div>
        </div>
      </article>
    </section>

    <section aria-label="Findings">
      <h2>发现的问题</h2>
      <ul>
        <li>&lt;Severity&gt; | &lt;Check&gt; | &lt;Evidence&gt; | &lt;Impact&gt;</li>
      </ul>
    </section>

    <section aria-label="Open Questions">
      <h2>待确认问题</h2>
      <ul><li class="empty">无</li></ul>
    </section>

    <section aria-label="Recommended Next Step">
      <h2>建议下一步</h2>
      <p>&lt;one concrete next step&gt;</p>
    </section>

    <section aria-label="Approval Checklist">
      <h2>人工批准清单</h2>
      <ul class="checklist">
        <li><label><input type="checkbox"> &lt;unit label&gt;：&lt;approval item&gt;</label></li>
        <li><label><input type="checkbox"> Program 最终验收：&lt;final acceptance item&gt;</label></li>
      </ul>
    </section>
  </main>
</body>
</html>
```
