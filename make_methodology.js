// Generates METHODOLOGY - SJFI 500 Quality-Value Index Ground Rules v1.0
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  TableOfContents, PageBreak, LevelFormat, PageNumber, Footer, Header,
} = require("docx");
const fs = require("fs");

const FONT = "Calibri";
const NAVY = "1F3B5C";
const GREY = "595959";

const body = (t, o = {}) => new Paragraph({
  spacing: { after: 120, line: 276 },
  children: [new TextRun({ text: t, font: FONT, size: 21, ...o.run })],
  ...o.para,
});
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 160 }, children: [new TextRun({ text: t, font: FONT, size: 30, bold: true, color: NAVY })] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 }, children: [new TextRun({ text: t, font: FONT, size: 24, bold: true, color: NAVY })] });
const bullet = (t) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 80 }, children: [new TextRun({ text: t, font: FONT, size: 21 })] });
const formula = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 120 }, children: [new TextRun({ text: t, font: "Cambria Math", size: 22, italics: true })] });

function table(headers, rows, colDxa) {
  const total = colDxa.reduce((a, b) => a + b, 0);
  const mkRow = (cells, isHead) => new TableRow({
    tableHeader: isHead,
    children: cells.map((t, i) => {
      return new TableCell({
        width: { size: colDxa[i], type: WidthType.DXA },
        shading: isHead ? { type: ShadingType.CLEAR, fill: NAVY } : undefined,
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ children: [new TextRun({ text: t, font: FONT, size: 19, bold: isHead, color: isHead ? "FFFFFF" : "000000" })] })],
      });
    }),
  });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: colDxa,
    rows: [mkRow(headers, true), ...rows.map((r) => mkRow(r, false))],
  });
}
const spacer = () => new Paragraph({ spacing: { after: 120 }, children: [] });

// ------------------------------------------------------------------ content
const cover = [
  new Paragraph({ spacing: { before: 2400 }, children: [] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "GROUND RULES", font: FONT, size: 26, color: GREY, characterSpacing: 60 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 240, after: 240 }, children: [new TextRun({ text: "SJFI 500 Quality-Value Factor Index", font: FONT, size: 52, bold: true, color: NAVY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Index Methodology  ·  Version 1.0  ·  July 2026", font: FONT, size: 24, color: GREY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 3600 }, children: [new TextRun({ text: "Accompanied by a full reference implementation and automated test suite", font: FONT, size: 20, color: GREY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 }, children: [new TextRun({ text: "Demonstration methodology backtested on a disclosed synthetic universe. Not an investable product.", font: FONT, size: 18, italics: true, color: GREY })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

const toc = [
  h1("Contents"),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] }),
];

const s1 = [
  h1("1. Introduction"),
  h2("1.1 Purpose and objective"),
  body("The SJFI 500 Quality-Value Factor Index (\u201Cthe Index\u201D) is designed to represent the performance of securities in a broad-market parent universe, with constituent weights tilted toward securities exhibiting favourable Value and Quality characteristics, subject to eligibility screening and single-constituent capping. The Index is intended to be transparent, rules-based and replicable: every rule in this document maps to a specific, tested function in the accompanying reference implementation (Appendix A)."),
  h2("1.2 Index variants"),
  body("Two variants are calculated daily from the same constituent basket:"),
  bullet("Price Index (PI) \u2013 reflects constituent price movements only."),
  bullet("Total Return Index (TR) \u2013 reflects price movements plus ordinary cash dividends, reinvested across the whole index basket on the ex-dividend date."),
  h2("1.3 Base date and base value"),
  body("The Index is chained from a base value of 1000.0 at the close of the first review effective date within the calculation history. All subsequent levels follow the divisor arithmetic of Section 8."),
  h2("1.4 Governance statement"),
  body("These Ground Rules follow the structure and disclosure principles of the IOSCO Principles for Financial Benchmarks (July 2013), in particular Principles 11\u201313 on transparency of benchmark determinations, availability of methodology, and rationale for material changes."),
  h2("1.5 Important disclosure \u2013 synthetic data"),
  body("The reference backtest is computed on a fully synthetic 500-security universe (2010\u20132025) generated by a disclosed data-generating process that embeds modest value and quality premia (2.0% and 1.5% per annum respectively at unit factor loading) alongside market, sector and idiosyncratic risk, plus simulated splits, dividends, delistings and IPOs. Backtest results therefore illustrate the mechanics and risk characteristics of the methodology; they are not evidence of live factor efficacy. The data layer is an adapter boundary: any point-in-time equity dataset (e.g. CRSP, LSEG/Refinitiv) can be substituted without modification to the calculation engine.", { run: { italics: true } }),
];

const s2 = [
  h1("2. Management responsibilities"),
  h2("2.1 Rule ownership and methodology review"),
  body("The index owner is responsible for the daily operation of the Index and for the interpretation and application of these Ground Rules. The methodology is reviewed at least annually. Material changes are versioned, documented with rationale, and applied only from a future effective date; methodology changes are never applied retrospectively."),
  h2("2.2 Expert judgement"),
  body("Where an event occurs that is not explicitly covered by these Ground Rules, treatment is determined by reference to the closest analogous rule, with the overriding objectives of (i) index level continuity, (ii) replicability by a passive tracker, and (iii) minimisation of unnecessary turnover. Any exercise of expert judgement is recorded in the review audit log."),
  h2("2.3 Restatement policy"),
  body("If an index level is found to have been calculated in error, it is restated where the error is discovered within two business days of publication. Errors discovered later are corrected on a forward-looking basis only, with a public notice describing the nature and magnitude of the error."),
];

const s3 = [
  h1("3. Eligible universe"),
  h2("3.1 Parent universe"),
  body("The parent universe comprises all securities in the data provider\u2019s coverage of the target market (in the reference implementation, the full synthetic universe of 500 securities). Eligibility is assessed at each review using only information publicly available on the review cut-off date (point-in-time discipline; see Section 6.3)."),
  h2("3.2 Eligibility screens"),
  body("A security must pass all of the following screens to be eligible:"),
  table(
    ["Screen", "Rule", "Parameter"],
    [
      ["Listing status", "Traded (valid close price) on the cut-off date", "\u2014"],
      ["Seasoning", "Minimum trading history", "126 trading days"],
      ["Free float", "Free-float factor at least the minimum", "5%"],
      ["Liquidity (value)", "Median daily traded value over trailing window", "\u2265 1.0m, 126-day window"],
      ["Liquidity (continuity)", "Fraction of days traded in window", "\u2265 90%"],
      ["Minimum price", "Close price on cut-off date", "\u2265 1.00"],
      ["Fundamental coverage", "A point-in-time fundamental record exists", "\u2014"],
    ],
    [2300, 4700, 2300]
  ),
  spacer(),
  body("Per-screen pass/fail results are retained for every security at every review, providing a complete audit trail of universe construction."),
];

const s4 = [
  h1("4. Factor definitions and scoring"),
  h2("4.1 Factor components"),
  table(
    ["Pillar", "Component", "Direction"],
    [
      ["Value", "Earnings yield (trailing 12m EPS / price)", "Higher is better"],
      ["Value", "Book-to-price", "Higher is better"],
      ["Quality", "Return on equity", "Higher is better"],
      ["Quality", "Leverage (debt-to-assets)", "Lower is better (sign-flipped)"],
      ["Quality", "Earnings variability", "Lower is better (sign-flipped)"],
    ],
    [1600, 5100, 2600]
  ),
  spacer(),
  body("Per-share fundamentals and prices are placed on a consistent share basis before ratio computation using the cumulative split adjustment factor, ensuring that corporate actions between the reporting date and the cut-off do not distort valuation ratios."),
  h2("4.2 Scoring pipeline"),
  bullet("Step 1 \u2013 Compute raw component ratios for all eligible securities as of the cut-off date."),
  bullet("Step 2 \u2013 Standardise each component cross-sectionally within the eligible universe (z-score), winsorised at \u00B13."),
  bullet("Step 3 \u2013 Pillar composite z-score = equal-weighted mean of available component z-scores."),
  bullet("Step 4 \u2013 Map each pillar composite to a tilt score in (0,1) via the standard normal CDF: S = \u03A6(z)."),
  bullet("Step 5 \u2013 Security score = S(Value) \u00D7 S(Quality) (multiplicative multi-factor tilt)."),
  body("Z-scores are computed within the eligible universe only. Scoring against ineligible securities would contaminate the cross-sectional distribution used for standardisation."),
];

const s5 = [
  h1("5. Index construction: weighting and capping"),
  h2("5.1 Target weights"),
  body("At each review, the uncapped target weight of eligible security i is proportional to its free-float-adjusted market capitalisation multiplied by its factor score:"),
  formula("w(i)  \u221D  FreeFloatMcap(i) \u00D7 Score(i)"),
  body("This is a broad tilt construction: all eligible securities remain in the Index with weights shifted toward high-scoring names, preserving capacity and limiting turnover relative to selection-based approaches."),
  h2("5.2 Single-constituent capping"),
  body("No constituent may exceed 5% of the Index at the review effective date. Capping uses the standard iterative redistribution algorithm:"),
  bullet("(a) Identify all constituents whose weight exceeds the cap; fix them at the cap."),
  bullet("(b) Redistribute the excess weight pro-rata across all uncapped constituents."),
  bullet("(c) Repeat (a)\u2013(b) until no uncapped constituent breaches the cap."),
  body("The algorithm terminates because the capped set strictly grows at each iteration, and is feasible whenever N \u00D7 cap \u2265 1. Weights may drift through the cap between reviews; no intra-review re-capping is performed."),
];

const s6 = [
  h1("6. Periodic review"),
  h2("6.1 Review frequency and calendar"),
  table(
    ["Milestone", "Definition"],
    [
      ["Frequency", "Semi-annual (March and September)"],
      ["Cut-off date", "Last trading day of February / August; all data as of this date"],
      ["Announcement date", "10 business days before the effective date"],
      ["Effective date", "After the close of the third Friday of March / September; new basket applies from the next open"],
    ],
    [2600, 6700]
  ),
  spacer(),
  h2("6.2 Actions at review"),
  body("At each review the eligible universe is re-screened, factor scores are recomputed, target weights are re-derived and re-capped, and index shares are reset so that the new basket\u2019s market value equals the old basket\u2019s market value at the effective-date close (Section 8.3). Securities failing eligibility exit; newly eligible securities enter. There are no intra-review additions: a constituent deleted between reviews is not replaced until the next review."),
  h2("6.3 Point-in-time discipline"),
  body("All review inputs are restricted to information publicly available on or before the cut-off date. Fundamental records carry an explicit publication date (reporting lag), and the engine selects the latest record published on or before the cut-off. This eliminates look-ahead bias by construction rather than by convention."),
];

const s7 = [
  h1("7. Corporate actions and events"),
  body("The table below sets out the treatment of corporate actions. Events marked \u2713 are exercised by the reference implementation and covered by automated tests; events marked \u25CB follow documented standard treatment but are not simulated by the synthetic data generator."),
  table(
    ["Event", "Price index treatment", "Divisor", "Impl."],
    [
      ["Share split / consolidation (r-for-1)", "Index shares multiplied by r at the open of the ex-date; price adjusts mechanically; basket value unchanged", "No change", "\u2713"],
      ["Ordinary cash dividend", "Price index unaffected; TR index reinvests the cash across the whole basket on the ex-date", "No change", "\u2713"],
      ["Deletion (delisting, failure)", "Removed at last available close price after the close of the preceding day", "Adjusted", "\u2713"],
      ["New listing (IPO)", "Considered for inclusion at the next review, subject to seasoning screen", "n/a", "\u2713"],
      ["Special (capital) dividend", "Price adjustment on ex-date equal to the special dividend", "Adjusted", "\u25CB"],
      ["Rights issue", "Price adjusted by theoretical ex-rights terms; index shares increased at subscription ratio", "Adjusted", "\u25CB"],
      ["Spin-off", "Spun entity included at zero price on ex-date, then removed at first trade price unless eligible", "Adjusted", "\u25CB"],
      ["Merger / acquisition of constituent", "Acquired line deleted at final terms; acquirer shares updated if constituent", "Adjusted", "\u25CB"],
      ["Suspension", "Carried at last price up to 10 trading days, then deleted at last price (or at nil where written down)", "On deletion", "\u25CB"],
    ],
    [2600, 4200, 1300, 800]
  ),
];

const s8 = [
  h1("8. Index calculation"),
  h2("8.1 Price index"),
  formula("PI(t)  =  \u03A3 n(i,t) \u00D7 p(i,t)  /  D(t)"),
  body("where n(i,t) is the number of index shares of constituent i (fixed between events), p(i,t) the unadjusted close price, and D(t) the divisor."),
  h2("8.2 Divisor adjustment"),
  body("Any event that changes basket market value without a market price movement (deletions; review rebalances) triggers a divisor adjustment applied after the close of day t\u22121:"),
  formula("D(t)  =  D(t\u22121) \u00D7 MV(t\u22121, new basket) / MV(t\u22121, old basket)"),
  body("so that the index level is continuous through the event. Share splits change n and p in exactly offsetting fashion and require no divisor adjustment."),
  h2("8.3 Review rebalancing"),
  body("At the effective-date close, new index shares are set as n(i) = w(i) \u00D7 MV(eff) / p(i, eff), where w(i) are the capped target weights and MV(eff) is the closing market value of the outgoing basket. Because the incoming basket\u2019s value equals the outgoing basket\u2019s value by construction, the divisor is unchanged and the index level is continuous."),
  h2("8.4 Total return index"),
  formula("TR(t)  =  TR(t\u22121) \u00D7 [ MV(t) + \u03A3 n(i,t) \u00D7 div(i,t) ]  /  MV(t\u22121, current basket)"),
  body("Ordinary cash dividends are reinvested across the whole index basket on the ex-dividend date. The price and total return indices are computed from the identical basket and divisor state."),
];

const s9 = [
  h1("9. Backtest protocol and results disclosure"),
  bullet("Universe: 500 synthetic securities, January 2010 \u2013 June 2025, including 12% delistings and 15% mid-sample IPOs \u2013 the backtest is free of survivorship bias by construction."),
  bullet("Benchmark: free-float cap-weighted parent index over the identical eligible universe, run through the identical calculation engine, so all differences are attributable to methodology."),
  bullet("Costs: review turnover is reported per review (two-way); an indicative cost drag is computed at 15bp per unit of two-way turnover."),
  bullet("Reproducibility: the entire backtest is deterministic given the disclosed random seed and regenerates from a single command (python run_backtest.py)."),
  body("Headline results on the reference synthetic path (seed 4): active return +1.5% p.a., tracking error 3.3%, information ratio 0.46, average review turnover 19% two-way (~0.06% p.a. estimated cost drag). These figures reflect premia deliberately embedded in the synthetic data-generating process and demonstrate that the methodology efficiently harvests a premium where one exists; they are not a forecast."),
];

const appA = [
  h1("Appendix A \u2013 Rule-to-code map"),
  table(
    ["Ground Rule", "Module / function", "Tested"],
    [
      ["\u00A73.2 Eligibility screens", "eligibility.apply_eligibility_screens", "audit trail cols"],
      ["\u00A74 Factor scoring", "factors.composite_factor_scores", "\u2014"],
      ["\u00A75.1 Tilt weights", "weighting.tilt_weights", "test_tilt_weights"],
      ["\u00A75.2 Capping", "weighting.apply_capping", "cap + feasibility tests"],
      ["\u00A76.1 Review calendar", "calendar.ReviewCalendar", "test_third_friday"],
      ["\u00A77 Split treatment", "engine.IndexEngine.run step (2)", "test_split_leaves_index_unchanged"],
      ["\u00A77 Deletion treatment", "engine.IndexEngine.run step (1)", "test_deletion_divisor_continuity"],
      ["\u00A77/8.4 Dividend / TR", "engine.IndexEngine.run step (3)", "test_dividend_lifts_tr_not_pi"],
      ["\u00A78.2\u20138.3 Divisor arithmetic", "engine.IndexEngine.run step (4)", "continuity tests"],
    ],
    [3400, 3900, 2000]
  ),
];

const appB = [
  h1("Appendix B \u2013 Glossary"),
  table(
    ["Term", "Definition"],
    [
      ["Divisor", "Scalar linking basket market value to the published index level; adjusted to preserve continuity through non-market events"],
      ["Free-float factor", "Fraction of shares outstanding available to ordinary investors"],
      ["Index shares", "Number of shares of a constituent held in the notional index basket"],
      ["Point-in-time", "Using only data publicly available at the as-of date, respecting publication lags"],
      ["Tilt score", "\u03A6(z) mapping of a composite factor z-score into (0,1)"],
      ["Two-way turnover", "0.5 \u00D7 \u03A3 |target weight \u2212 drifted weight| at a review"],
    ],
    [2600, 6700]
  ),
];

const doc = new Document({
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 240 } } } }] }] },
  features: { updateFields: true },
  styles: { default: { document: { run: { font: FONT, size: 21 } } } },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1200, bottom: 1200, left: 1300, right: 1300 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "SJFI 500 Quality-Value Index \u2013 Ground Rules v1.0", font: FONT, size: 16, color: GREY })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: GREY })] })] }) },
    children: [...cover, ...toc, ...s1, ...s2, ...s3, ...s4, ...s5, ...s6, ...s7, ...s8, ...s9, ...appA, ...appB],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("outputs/SJFI_500_Ground_Rules_v1.0.docx", buf);
  console.log("written");
});
