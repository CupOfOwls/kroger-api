import React, { useState, useRef } from "react";
import posthog from "posthog-js";
import styles from "./styles.module.css";

// MDX passes `question`/`label` as JSX nodes (they can contain inline <code>).
// Flatten to plain text so analytics carries readable strings, not element trees.
function nodeToText(node) {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(nodeToText).join("");
  if (node.props && node.props.children != null)
    return nodeToText(node.props.children);
  return "";
}

// "Knowledge check 1" -> "knowledge-check-1": a short, stable slug that reads
// well as a chart axis label, unlike the full question sentence.
function slugify(text) {
  return String(text)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

// Last path segment of the current page, e.g. "use-the-kroger-api". Used to
// namespace quiz ids so "Knowledge check 1" on two different tutorials do not
// collide into one series.
function currentPageSlug() {
  if (typeof window === "undefined") return "index";
  return window.location.pathname.replace(/\/+$/, "").split("/").pop() || "index";
}

/**
 * A small formative-assessment widget: the reader commits to an answer
 * before seeing any feedback. Feedback narrates the consequence of the
 * chosen answer rather than announcing right/wrong, so a wrong pick still
 * teaches. Readers can try other options after choosing.
 *
 * Analytics: each click fires a `quiz_answer` event. Alongside the full
 * `question`/`choice` text (kept for drill-down), it sends short, stable keys
 * built for legible chart axes:
 *   - `quiz_id`      page-namespaced slug, e.g. "use-the-kroger-api:knowledge-check-1"
 *   - `quiz_title`   "Knowledge check 1"
 *   - `choice_letter` "A" / "B" / "C"
 *   - `attempt` / `first_attempt` — the widget invites retries, so filter to
 *     first_attempt to measure genuine first-try correctness.
 *
 * Usage (MDX):
 *   <Quiz
 *     question="..."
 *     options={[
 *       { label: "...", feedback: "...", correct: false },
 *       { label: "...", feedback: "...", correct: true },
 *     ]}
 *   />
 * Pass an explicit `id` to pin the analytics key if the title or slug changes.
 */
export default function Quiz({ id, title, question, options }) {
  const [selected, setSelected] = useState(null);
  const attemptRef = useRef(0);

  return (
    <div className={styles.quiz}>
      {title && <div className={styles.title}>{title}</div>}
      <div className={styles.question}>{question}</div>
      <div className={styles.options}>
        {options.map((opt, i) => {
          const isSelected = selected === i;
          const stateClass = !isSelected
            ? ""
            : opt.correct
              ? styles.correct
              : styles.incorrect;
          return (
            <div key={i}>
              <button
                type="button"
                className={`${styles.option} ${stateClass}`}
                onClick={() => {
                  setSelected(i);
                  if (typeof window !== "undefined" && posthog.__loaded) {
                    attemptRef.current += 1;
                    const pageSlug = currentPageSlug();
                    posthog.capture("quiz_answer", {
                      quiz_id: id || `${pageSlug}:${slugify(title || "quiz")}`,
                      quiz_title: title,
                      page: pageSlug,
                      choice_letter: String.fromCharCode(65 + i),
                      choice: nodeToText(opt.label),
                      question: nodeToText(question),
                      correct: !!opt.correct,
                      result: opt.correct ? "correct" : "incorrect",
                      attempt: attemptRef.current,
                      first_attempt: attemptRef.current === 1,
                    });
                  }
                }}
                aria-pressed={isSelected}
              >
                <span className={styles.optionLetter} aria-hidden="true">
                  {String.fromCharCode(65 + i)}
                </span>
                <span>{opt.label}</span>
              </button>
              {isSelected && (
                <div
                  role="status"
                  aria-live="polite"
                  className={`${styles.feedback} ${
                    opt.correct ? styles.feedbackCorrect : ""
                  }`}
                >
                  {opt.feedback}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
