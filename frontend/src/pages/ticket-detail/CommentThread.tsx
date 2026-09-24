import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";
import { topLevelMessage } from "../../lib/form-errors";
import type { Comment } from "../../lib/types";

export function CommentThread({ ticketId }: { ticketId: string }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isStaff = user?.role === "agent" || user?.role === "admin";

  const { data, isLoading, isError, error: loadError } = useQuery({
    queryKey: ["comments", ticketId],
    queryFn: () => api.get<Comment[]>(`/tickets/${ticketId}/comments`),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post<Comment>(`/tickets/${ticketId}/comments`, { body, is_internal: isInternal }),
    onSuccess: () => {
      setBody("");
      setIsInternal(false);
      queryClient.invalidateQueries({ queryKey: ["comments", ticketId] });
    },
    onError: (err) => setError(topLevelMessage(err)),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    mutation.mutate();
  }

  return (
    <section aria-labelledby="comments-heading">
      <h2 id="comments-heading">Comments</h2>

      {isLoading && <p>Loading comments...</p>}
      {isError && <p role="alert">{topLevelMessage(loadError)}</p>}

      <ul>
        {data?.map((comment) => (
          <li key={comment.id}>
            <p>
              <strong>{comment.author.full_name}</strong>
              {comment.is_internal && <span> (internal note)</span>}
            </p>
            <p>{comment.body}</p>
          </li>
        ))}
      </ul>

      <form onSubmit={handleSubmit}>
        <label htmlFor="comment-body">Add a comment</label>
        <textarea
          id="comment-body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          required
        />

        {isStaff && (
          <label>
            <input
              type="checkbox"
              checked={isInternal}
              onChange={(e) => setIsInternal(e.target.checked)}
            />
            Internal note (not visible to the customer)
          </label>
        )}

        {error && <p role="alert">{error}</p>}

        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Posting..." : "Post"}
        </button>
      </form>
    </section>
  );
}
