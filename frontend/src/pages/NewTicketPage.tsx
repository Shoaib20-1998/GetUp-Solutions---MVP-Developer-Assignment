import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../lib/api";
import { fieldErrors, topLevelMessage } from "../lib/form-errors";
import type { Category, Priority, Ticket } from "../lib/types";

const CATEGORY_OPTIONS: Category[] = ["billing", "technical", "account", "general"];
const PRIORITY_OPTIONS: Priority[] = ["low", "medium", "high", "urgent"];

export function NewTicketPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<Category>("general");
  const [priority, setPriority] = useState<Priority>("medium");
  const [file, setFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErrors({});
    setFormError(null);
    setIsSubmitting(true);

    try {
      const ticket = await api.post<Ticket>("/tickets", {
        title,
        description,
        category,
        priority,
      });

      if (file) {
        const form = new FormData();
        form.append("file", file);
        try {
          await api.postForm(`/tickets/${ticket.id}/attachments`, form);
        } catch (attachErr) {
          // The ticket already exists; surface the attachment failure but
          // still route to it rather than losing the created ticket.
          setFormError(topLevelMessage(attachErr));
          navigate(`/tickets/${ticket.id}`);
          return;
        }
      }

      navigate(`/tickets/${ticket.id}`);
    } catch (err) {
      const fields = fieldErrors(err);
      if (Object.keys(fields).length > 0) {
        setErrors(fields);
      } else {
        setFormError(topLevelMessage(err));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main>
      <h1>New ticket</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="title">Title</label>
        <input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        {errors.title && <p role="alert">{errors.title}</p>}

        <label htmlFor="description">Description</label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
        />
        {errors.description && <p role="alert">{errors.description}</p>}

        <label htmlFor="category">Category</label>
        <select
          id="category"
          value={category}
          onChange={(e) => setCategory(e.target.value as Category)}
        >
          {CATEGORY_OPTIONS.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <label htmlFor="priority">Priority</label>
        <select
          id="priority"
          value={priority}
          onChange={(e) => setPriority(e.target.value as Priority)}
        >
          {PRIORITY_OPTIONS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>

        <label htmlFor="attachment">Attachment (optional)</label>
        <input
          id="attachment"
          type="file"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />

        {formError && <p role="alert">{formError}</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Submitting..." : "Create ticket"}
        </button>
      </form>
    </main>
  );
}
