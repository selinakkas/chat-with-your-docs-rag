import { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const uploadFile = async () => {
    if (!file) {
      alert("Please select a file");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);

      const response = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      alert(data.message);
    } catch (error) {
      console.error(error);
      alert("Upload failed");
    } finally {
      setLoading(false);
    }
  };

  const askQuestion = async () => {
    if (!query) {
      alert("Please enter a question");
      return;
    }

    try {
      setLoading(true);

      const response = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,
        }),
      });

      const data = await response.json();

      setAnswer(data.answer);
    } catch (error) {
      console.error(error);
      alert("Question request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "40px", fontFamily: "Arial" }}>
      <h1>Chat With Your Docs</h1>

      <div style={{ marginBottom: "20px" }}>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files[0])}
        />

        <button onClick={uploadFile}>
          Upload File
        </button>
      </div>

      <div style={{ marginBottom: "20px" }}>
        <input
          type="text"
          placeholder="Ask something..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ width: "300px" }}
        />

        <button onClick={askQuestion}>
          Ask
        </button>
      </div>

      {loading && <p>Loading...</p>}

      {answer && (
        <div>
          <h3>Answer:</h3>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
}

export default App;