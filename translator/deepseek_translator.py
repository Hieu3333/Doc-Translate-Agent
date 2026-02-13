import os
from typing import List, Dict, Any
import json
import threading
from queue import Queue
import re

class DeepseekTranslator:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
        
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
        except ImportError:
            raise ImportError("OpenAI library is not installed. Run: pip install openai")
        
        # DeepSeek pricing
        self.cost_table = {
            "deepseek-chat": {"input": 0.028, "output": 0.42},
            "deepseek-reasoner": {"input": 0.028, "output": 0.42},
        }

    def _parse_llm_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse the LLM response and extract JSON array.
        Handles various response formats (wrapped in markdown, extra whitespace, etc.)
        """
        # Try to extract JSON array from the response
        # First, try direct parsing
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON array pattern
        array_match = re.search(r'\[\s*{[\s\S]*}\s*\]', response_text)
        if array_match:
            try:
                return json.loads(array_match.group(0))
            except json.JSONDecodeError:
                pass
        
        raise ValueError(f"Failed to parse LLM response as JSON: {response_text[:200]}...")

    def _translate_batch(self, batch_texts: List[str], batch_id: int, source_language: str, 
                         target_language: str, context: str, model: str, results_queue: Queue) -> None:
        """
        Translate a batch of texts and store results in the queue.
        """
        try:
            system_prompt = f"""You are a professional translator.

    Requirements:
    - Translate the following list of text objects, each with an "id" and "text" field.
    - This list of texts comes from the same document, so ensure consistency in terminology and style.
    - Translate the content (text field) from {source_language} to {target_language}.
    - Return a list of objects preserving their order, ids, and structure.
    - Maintain consistency in terminology and style across all translations.
    - Preserve the original formatting and structure of each segment.
    - Keep technical terms accurate and appropriate.
    - Preserve the tone, style, and meaning.
    - Do not add explanations or additional content.
    - If text contains code, URLs, or special formatting, preserve them exactly.
    - Use the document context to ensure consistent translation of repeated terms and concepts.
    - Translate every element in the list. Do not omit, summarize, or merge any element.
    - If an element looks like a diagram, label, arrow, or code, still translate it or return the original text unchanged.
    - The output list must have the exact same length and order as the input list.
    - Empty strings are not allowed.

    Return format:
    - Return ONLY a valid JSON array of objects.
    - Each object must have the same "id" and a translated "text" field.
    - The array length MUST equal the input list length.
    - Each element corresponds to the input at the same index.
    - Never return null, omit elements, or change order.
    - Example: [{{"id": 0, "text": "translated text 0"}}, {{"id": 1, "text": "translated text 1"}}]
"""
            if context:
                system_prompt += f"\n\nDocument context:\n{context}"
            
            processed_texts = [{"id": idx, "text": text} for idx, text in enumerate(batch_texts)]
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(processed_texts)}
                ],
                "temperature": 0.3
            }
            
            response = self.client.chat.completions.create(**kwargs)
            response_text = response.choices[0].message.content
            
            # Parse the LLM response
            translated_batch = self._parse_llm_response(response_text)
            
            # Extract token usage information
            token_usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
            
            # Store results in queue with batch_id for proper ordering
            results_queue.put((batch_id, translated_batch, token_usage))
        except Exception as e:
            results_queue.put((batch_id, {"error": str(e)}, None))

    def translate_texts(self, texts: List[str], source_language: str, target_language: str, model: str,
                       context: str = "", batch_size: int = 10) -> Dict[str, Any]:
        """
        Translate texts in batches using parallel threads.
        
        Args:
            texts: List of strings to translate
            source_language: Source language
            target_language: Target language
            model: The model to use for translation
            context: Optional document context for consistent translation
            batch_size: Number of texts to translate per batch
        
        Returns:
            Dictionary with "translations" (list of strings) and "total_cost" (float)
        """
        if not texts:
            return {
                "translations": [],
                "total_cost": 0.0
            }
        
        # Split texts into batches
        batches = []
        for i in range(0, len(texts), batch_size):
            batches.append(texts[i:i + batch_size])
        
        # Create queue for results
        results_queue: Queue = Queue()
        threads = []
        
        # Start threads for each batch
        for batch_id, batch_texts in enumerate(batches):
            thread = threading.Thread(
                target=self._translate_batch,
                args=(batch_texts, batch_id, source_language, target_language, context, model, results_queue)
            )
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results in order
        batch_results = {}
        token_usage_list = []
        while not results_queue.empty():
            batch_id, result, token_usage = results_queue.get()
            batch_results[batch_id] = result
            if token_usage:
                token_usage_list.append(token_usage)
        
        # Check for errors
        for batch_id, result in batch_results.items():
            if isinstance(result, dict) and "error" in result:
                raise RuntimeError(f"Error translating batch {batch_id}: {result['error']}")
        
        # Reconstruct the full list of translations
        all_translations = []
        for batch_id in range(len(batches)):
            batch_translations = batch_results[batch_id]
            for item in batch_translations:
                all_translations.append(item.get("text", ""))
        
        # Calculate total cost
        total_cost = 0.0
        model_pricing = self.cost_table.get(model)
        
        if model_pricing:
            for token_usage in token_usage_list:
                input_cost = (token_usage["input_tokens"] / 1_000_000) * model_pricing["input"]
                output_cost = (token_usage["output_tokens"] / 1_000_000) * model_pricing["output"]
                total_cost += input_cost + output_cost
        
        return {
            "translations": all_translations,
            "total_cost": total_cost
        }
