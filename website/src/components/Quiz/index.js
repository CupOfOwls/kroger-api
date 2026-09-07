import React, { useState } from "react";
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

/**
 * A small formative-assessment widget: the reader commits to an answer
 * before seeing any feedback. Feedback narrates the consequence of the
 * chosen answer rather than announcing right/wrong, so a wrong pick still
 * teaches. Readers can try other options after choosing.
 *
 * Usage (MDX):
 *   <Quiz
 *     question="..."
 *     options={[
 *       { label: "...", feedback: "...", correct: false },
 *       { label: "...", feedback: "...", correct: true },
 *     ]}
 *   />
 */
export default function Quiz({ title, question, options }) {
  const [selected, setSelected] = useState(null);

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
                    posthog.capture("quiz_answer", {
                      question: nodeToText(question),
                      choice: nodeToText(opt.label),
                      correct: !!opt.correct,
                      result: opt.correct ? "correct" : "incorrect",
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
