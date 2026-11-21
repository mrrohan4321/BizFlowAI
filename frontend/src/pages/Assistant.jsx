
import React, { useEffect, useRef, useState } from 'react';
import {
  ArrowUp,
  Bot,
  LoaderCircle,
  MessageCircle,
  Sparkles,
  UserRound
} from 'lucide-react';

import { askAssistant } from '../services/assistant';
import { ErrorBox, PageHead } from '../components/UI';

const suggestions = [
  'How much do customers owe me?',
  'Which invoices are overdue?',
  'How did my business perform?',
  'What is my expected cash flow?',
  'How much do I owe suppliers?'
];

export default function Assistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const end = useRef(null);

  // FIX: Do not implicitly return the result of scrollIntoView().
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function send(question) {
    const q = (question || input).trim();

    if (!q || loading) return;

    setInput('');
    setMessages(s => [...s, { role: 'user', text: q }]);
    setLoading(true);
    setError(null);

    try {
      const response = await askAssistant(q);

      setMessages(s => [
        ...s,
        {
          role: 'assistant',
          ...response,
          text: response.answer
        }
      ]);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHead
        eyebrow="YOUR FINANCIAL COPILOT"
        title="Ask BizFlow AI"
        subtitle="Get answers grounded in your actual business records."
      />

      <div className="chat-shell">
        <div className="chat-head">
          <div className="chat-avatar">
            <Bot size={23} />
          </div>

          <div>
            <strong>BizFlow AI Assistant</strong>
            <small>
              <span className="online-dot" />
              Ready to help you understand your finances
            </small>
          </div>

          <span className="chat-head-tag">
            <Sparkles size={14} /> DATA-GROUNDED
          </span>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-welcome">
              <div className="chat-welcome-icon">
                <Sparkles size={30} />
              </div>

              <h2>Financial clarity starts here.</h2>

              <p>
                Ask a question in plain language. I'll find answers using
                your real business data.
              </p>

              <div className="suggestions">
                {suggestions.map(s => (
                  <button key={s} onClick={() => send(s)}>
                    {s}
                    <ArrowUp size={15} />
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`message ${m.role}`}>
              <div className="message-avatar">
                {m.role === 'user'
                  ? <UserRound size={17} />
                  : <Bot size={19} />}
              </div>

              <div className="bubble">
                <div className="message-text">
                  {m.text || 'No answer available.'}
                </div>

                {m.insufficient_data && (
                  <p className="ai-caveat">
                    More business data is needed for a confident answer.
                  </p>
                )}

                {m.tool_used && (
                  <small className="tool-used">
                    Calculated by: {m.tool_used}
                  </small>
                )}

                {m.data_used && (
                  <details className="used-data">
                    <summary>View supporting data</summary>
                    <pre>
                      {JSON.stringify(m.data_used, null, 2)}
                    </pre>
                  </details>
                )}

                {m.follow_up && (
                  <div className="followups">
                    {(Array.isArray(m.follow_up)
                      ? m.follow_up
                      : [m.follow_up]
                    )
                      .filter(Boolean)
                      .map((f, j) => (
                        <button
                          key={j}
                          onClick={() =>
                            send(
                              typeof f === 'string'
                                ? f
                                : f.question || String(f)
                            )
                          }
                        >
                          {typeof f === 'string'
                            ? f
                            : f.question || String(f)}
                        </button>
                      ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="message-avatar">
                <Bot size={19} />
              </div>

              <div className="bubble">
                <LoaderCircle className="spinner" size={19} />
                Thinking through your numbers…
              </div>
            </div>
          )}

          {error && (
            <ErrorBox
              error={error}
              onRetry={() => {
                const latest = [...messages]
                  .reverse()
                  .find(m => m.role === 'user');

                if (latest) send(latest.text);
              }}
            />
          )}

          <div ref={end} />
        </div>

        <div className="chat-composer">
          <form
            onSubmit={e => {
              e.preventDefault();
              send();
            }}
          >
            <label className="sr-only" htmlFor="chat-question">
              Ask a financial question
            </label>

            <input
              id="chat-question"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about cash flow, invoices, payments…"
              maxLength={500}
            />

            <button
              aria-label="Send message"
              disabled={!input.trim() || loading}
            >
              <ArrowUp size={20} />
            </button>
          </form>

          <small>
            Answers use your business records. Confirm important financial
            decisions independently.
          </small>
        </div>
      </div>
    </>
  );
}
