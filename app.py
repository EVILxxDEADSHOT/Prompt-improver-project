from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import torch
import joblib
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from sklearn.metrics.pairwise import cosine_similarity


# Load dataset + precomputed weights
df = pd.read_csv("clean_final_processed.csv")
tfidf = joblib.load("tfidf_vectorizer.pkl")
tfidf_matrix = joblib.load("tfidf_matrix.pkl")
embeddings = torch.load("embeddings.pt", map_location=torch.device('cpu'))  # Ensure tensor loaded on CPU


# Load embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")


# Gemini API key - Replace with your actual API key
genai.configure(api_key="ENTER YOUTR GEMINI API KEY HERE")


def call_gemini_llm(prompt, model="gemini-2.5-pro", temperature=0.7):
    response = genai.GenerativeModel(model).generate_content(prompt)
    return response.text.strip()


# Class to generate prompts with retrieval
class PromptGenerator:
    def __init__(self, df, tfidf, tfidf_matrix, embed_model, embeddings):
        self.df = df
        self.tfidf = tfidf
        self.tfidf_matrix = tfidf_matrix
        self.embed_model = embed_model
        self.embeddings = embeddings.cpu()  # Ensure embeddings on CPU

    def extract_keywords(self, text, top_k=10):
        vec = self.tfidf.transform([text])
        scores = vec.toarray().flatten()
        indices = scores.argsort()[-top_k:][::-1]
        return [self.tfidf.get_feature_names_out()[i] for i in indices if scores[i] > 0]

    def retrieve_tfidf(self, text, top_k=5, min_similarity=0.3):
        vec = self.tfidf.transform([text])
        sims = cosine_similarity(vec, self.tfidf_matrix).flatten()
        idxs = sims.argsort()[::-1]
        return [
            self.df.iloc[i]["enhanced"]
            for i in idxs[:top_k] if sims[i] >= min_similarity
        ]

    def retrieve_embed(self, text, top_k=5, min_similarity=0.3):
        emb = self.embed_model.encode([text], convert_to_tensor=True).cpu()  # Move to CPU
        sims = torch.nn.functional.cosine_similarity(emb, self.embeddings)
        sims = sims.numpy()
        idxs = sims.argsort()[::-1]
        return [
            self.df.iloc[i]["enhanced"]
            for i in idxs[:top_k] if sims[i] >= min_similarity
        ]

    def generate(self, user_prompt, method="embed", top_k=5, min_similarity=0.35, llm_on_fallback=True):
        keywords = self.extract_keywords(user_prompt)

        # Step 1: Retrieve candidate matches
        retrieved = (self.retrieve_embed(user_prompt, top_k, min_similarity)
                     if method == "embed" else
                     self.retrieve_tfidf(user_prompt, top_k, min_similarity))

        if retrieved:
            dataset_style = retrieved[0]  # best improvised example
            draft_prompt = f"""
            You are a professional prompt improver.

            User original prompt: "{user_prompt}"
            Extracted keywords: {keywords}
            Example improvised prompt from dataset (to use as structural style guide): "{dataset_style}"

            Task:
            - Rewrite the user's prompt into a polished, clear, and contextually accurate improvised prompt.
            - Preserve the meaning and intent of the user prompt.
            - The final output must stay relevant to the user's original request.
            - The output can only be 2-3 lines long.
            """
            return call_gemini_llm(draft_prompt)

        else:
            if llm_on_fallback:
                return call_gemini_llm(
                    f"Rewrite this into a polished improvised prompt: {user_prompt}. "
                    f"Keywords: {keywords}. Only 2-3 lines."
                )
            else:
                return None


# Initialize generator
generator = PromptGenerator(df, tfidf, tfidf_matrix, embed_model, embeddings)


# Flask App
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@app.route("/improve", methods=["POST"])
def improve():
    data = request.json
    prompt = data.get("prompt", "")
    improved = generator.generate(prompt)
    return jsonify({"improved": improved})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
