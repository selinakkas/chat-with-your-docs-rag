import { useState } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [uploadMessage, setUploadMessage] = useState("");
  const [error, setError] = useState("");
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [loadingAsk, setLoadingAsk] = useState(false);

  const uploadFile = async () => {
    if (!file) {
      setError("Please select a file first.");
      return;
    }

    setError("");
    setUploadMessage("");
    setAnswer("");
    setSources([]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoadingUpload(true);

      const response = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setUploadMessage(
        `${data.file.filename} uploaded successfully. Indexed ${data.chunk_count} chunk(s).`
      );
    } catch (err) {
      setError(err.message || "Upload failed.");
    } finally {
      setLoadingUpload(false);
    }
  };

  const askQuestion = async () => {
    if (!query.trim()) {
      setError("Please enter a question.");
      return;
    }

    setError("");
    setAnswer("");
    setSources([]);

    try {
      setLoadingAsk(true);

      const response = await fetch("http://127.0.0.1:8000/ask/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        let errorMessage = "Question request failed.";

        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch {
          // response JSON değilse fallback
        }

        throw new Error(errorMessage);
      }

      if (!response.body) {
        throw new Error("Streaming response is not supported by the browser.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          const line = event
            .split("\n")
            .find((l) => l.startsWith("data: "));

          if (!line) continue;

          const jsonStr = line.replace("data: ", "").trim();

          if (!jsonStr) continue;

          try {
            const parsed = JSON.parse(jsonStr);

            if (parsed.type === "token") {
              setAnswer((prev) => prev + (parsed.content || ""));
            } else if (parsed.type === "sources") {
              setSources(parsed.content || []);
            } else if (parsed.type === "error") {
              throw new Error(parsed.content || "Streaming failed.");
            } else if (parsed.type === "done") {
              // stream tamamlandı
            }
          } catch (parseError) {
            console.error("Stream parse error:", parseError);
          }
        }
      }
    } catch (err) {
      setError(err.message || "Question request failed.");
    } finally {
      setLoadingAsk(false);
    }
  };

  const busy = loadingUpload || loadingAsk;

  return (
    <div className="page">
      <div className="background-glow glow-1" />
      <div className="background-glow glow-2" />

      <main className="app-shell">
        <section className="hero-card">
          <div className="hero-badge">RAG Demo</div>
          <h1>Chat With Your Docs</h1>
          <p>
            Upload a document, ask a question, and get an answer grounded in
            your files.
          </p>
        </section>

        <section className="panel-grid">
          <div className="panel">
            <div className="panel-header">
              <h2>1. Upload Document</h2>
              <span>PDF, TXT, DOCX</span>
            </div>

            <div className="upload-box">
              <label className="file-label">
                <input
                  type="file"
                  onChange={(e) => setFile(e.target.files[0])}
                />
                <span>{file ? file.name : "Choose a document"}</span>
              </label>

              <button
                className="primary-btn"
                onClick={uploadFile}
                disabled={loadingUpload}
              >
                {loadingUpload ? "Uploading..." : "Upload File"}
              </button>
            </div>

            {uploadMessage && <div className="success-box">{uploadMessage}</div>}
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>2. Ask a Question</h2>
              <span>Semantic search + streaming LLM answer</span>
            </div>

            <div className="question-box">
              <textarea
                className="query-input"
                placeholder="Ask something about your uploaded document..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={4}
              />

              <button
                className="primary-btn"
                onClick={askQuestion}
                disabled={loadingAsk}
              >
                {loadingAsk ? "Thinking..." : "Ask"}
              </button>
            </div>
          </div>
        </section>

        {error && <div className="error-box">{error}</div>}

        {busy && (
          <div className="loading-box">
            <div className="spinner" />
            <span>
              {loadingAsk
                ? "Generating answer in real time..."
                : "Processing your request..."}
            </span>
          </div>
        )}

        <section className="result-panel">
          <div className="panel-header">
            <h2>Answer</h2>
            <span>Streaming model response</span>
          </div>

          <div className="answer-box">
            {answer ? (
              <p>{answer}</p>
            ) : (
              <p className="placeholder-text">
                Your answer will appear here after you upload a document and ask
                a question.
              </p>
            )}
          </div>
        </section>

        <section className="result-panel">
          <div className="panel-header">
            <h2>Sources</h2>
            <span>Retrieved chunks</span>
          </div>

          {sources.length > 0 ? (
            <div className="sources-grid">
              {sources.map((source, index) => (
                <div
                  className="source-card"
                  key={`${source.document_id}-${index}`}
                >
                  <div className="source-top">
                    <h3>{source.filename}</h3>
                    <span className="chip">Chunk {source.chunk_index}</span>
                  </div>

                  <div className="source-meta">
                    <span>Document ID: {source.document_id}</span>
                    <span>
                      Distance:{" "}
                      {typeof source.distance === "number"
                        ? source.distance.toFixed(4)
                        : source.distance}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-sources">
              Source documents will appear here after a successful question.
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;