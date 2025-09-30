#!/usr/bin/env python3
"""
Test script for Versailles Agent using LLM-as-a-Judge
Evaluates agent responses against expected answers using Mistral as judge
"""

import asyncio
import json
import os
import time
import httpx
from typing import Dict, List, Tuple
from datetime import datetime
from dotenv import load_dotenv
from llama_index.llms.mistralai import MistralAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class LLMJudge:
    """LLM-as-a-Judge for evaluating agent responses"""
    
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is required")
        
        self.llm = MistralAI(model="mistral-large-latest", api_key=api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=15)
    )
    async def evaluate_response(
        self, 
        question: str, 
        expected_answer: str, 
        actual_answer: str
    ) -> Dict:
        """
        Evaluate the agent's response using LLM as judge with retry logic
        
        Returns:
            Dict with score (0-10), reasoning, and detailed metrics
        """
        
        evaluation_prompt = f"""You are an expert evaluator for a Versailles Palace chatbot. 
Your task is to evaluate the quality of the agent's response compared to the expected answer.

USER QUESTION:
{question}

EXPECTED ANSWER (Reference):
{expected_answer}

ACTUAL ANSWER (Agent's Response):
{actual_answer}

EVALUATION CRITERIA:
1. **Accuracy** (0-3 points): Does the answer contain correct information? Are there any factual errors?
2. **Completeness** (0-3 points): Does it cover all important points from the expected answer?
3. **Relevance** (0-2 points): Does it directly answer the question without unnecessary information?
4. **Helpfulness** (0-2 points): Is it practical and useful for the user?

SCORING GUIDE:
- 9-10: Excellent - Accurate, complete, and highly helpful
- 7-8: Good - Mostly accurate and complete with minor gaps
- 5-6: Acceptable - Contains key information but missing important details
- 3-4: Poor - Significant gaps or inaccuracies
- 0-2: Very Poor - Incorrect or unhelpful

Respond in JSON format (use ONLY plain text in strings, NO special characters or line breaks inside strings):
{{
    "total_score": 0-10,
    "accuracy_score": 0-3,
    "completeness_score": 0-3,
    "relevance_score": 0-2,
    "helpfulness_score": 0-2,
    "reasoning": "Brief explanation in ONE line",
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "missing_info": ["missing1", "missing2"]
}}

IMPORTANT: Keep all string values on a single line. Do not use line breaks inside strings.

Provide your evaluation:"""

        try:
            response = await self.llm.acomplete(evaluation_prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Clean control characters from JSON (but keep newlines and tabs)
            import re
            # Replace problematic control chars but keep \n and \t
            result_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', result_text)
            
            # Try to parse JSON with more lenient settings
            try:
                evaluation = json.loads(result_text, strict=False)
            except json.JSONDecodeError as json_err:
                print(f"JSON parse error: {json_err}")
                print(f"Problematic JSON (first 500 chars): {result_text[:500]}")
                raise
            
            return evaluation
            
        except Exception as e:
            print(f"Evaluation error: {e}")
            return {
                "total_score": 0,
                "accuracy_score": 0,
                "completeness_score": 0,
                "relevance_score": 0,
                "helpfulness_score": 0,
                "reasoning": f"Evaluation failed: {str(e)}",
                "strengths": [],
                "weaknesses": ["Evaluation error"],
                "missing_info": []
            }


class AgentTester:
    """Test harness for the Versailles Agent"""
    
    def __init__(self, test_queries_path: str = "test_queries.json", api_url: str = "http://localhost:8000"):
        self.test_queries_path = test_queries_path
        self.api_url = api_url
        self.judge = LLMJudge()
        self.results = []
    
    def load_test_queries(self) -> List[Dict]:
        """Load test queries from JSON file"""
        with open(self.test_queries_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError))
    )
    async def get_agent_response(self, question: str) -> str:
        """Get response from agent via API endpoint with retry logic"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Call evaluate endpoint
                response = await client.post(
                    f"{self.api_url}/chat",
                    json={
                        "question": question
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Extract answer from EvalCompletionAnswer response
                    answer = data.get("answer", "")
                    if not answer:
                        print(f"⚠️  Warning: Empty answer received, retrying...")
                        raise httpx.RequestError("Empty response from API")
                    return answer.strip()
                elif response.status_code in [429, 500, 502, 503, 504]:
                    # Retry on rate limit or server errors
                    print(f"⚠️  API returned {response.status_code}, retrying...")
                    response.raise_for_status()
                else:
                    return f"API Error: {response.status_code} - {response.text}"
                    
        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return error_msg
    
    async def test_single_query(self, test_case: Dict, index: int) -> Dict:
        """Test a single query and evaluate the response"""
        
        question = test_case["question"]
        expected_answer = test_case["answer"]
        
        print(f"\n{'='*100}")
        print(f"Test {index + 1}: {question[:100]}...")
        print(f"{'='*100}")
        
        # Get agent response
        print("🤖 Getting agent response...")
        start_time = time.time()
        actual_answer = await self.get_agent_response(question)
        response_time = time.time() - start_time
        
        print(f"⏱️  Response time: {response_time:.2f}s")
        print(f"\n📝 Agent's answer (first 200 chars):\n{actual_answer[:200]}...")
        
        # Evaluate response
        print("\n⚖️  Evaluating with LLM Judge...")
        evaluation = await self.judge.evaluate_response(
            question, expected_answer, actual_answer
        )
        
        # Display evaluation
        print(f"\n📊 Evaluation Results:")
        print(f"   Total Score: {evaluation['total_score']}/10")
        print(f"   - Accuracy: {evaluation['accuracy_score']}/3")
        print(f"   - Completeness: {evaluation['completeness_score']}/3")
        print(f"   - Relevance: {evaluation['relevance_score']}/2")
        print(f"   - Helpfulness: {evaluation['helpfulness_score']}/2")
        print(f"\n💭 Reasoning: {evaluation['reasoning']}")
        
        if evaluation['strengths']:
            print(f"\n✅ Strengths:")
            for strength in evaluation['strengths']:
                print(f"   • {strength}")
        
        if evaluation['weaknesses']:
            print(f"\n❌ Weaknesses:")
            for weakness in evaluation['weaknesses']:
                print(f"   • {weakness}")
        
        if evaluation['missing_info']:
            print(f"\n⚠️  Missing Information:")
            for missing in evaluation['missing_info']:
                print(f"   • {missing}")
        
        # Store result
        result = {
            "index": index + 1,
            "question": question,
            "expected_answer": expected_answer,
            "actual_answer": actual_answer,
            "response_time": response_time,
            "evaluation": evaluation
        }
        
        return result
    
    async def run_all_tests(self, limit: int = None) -> List[Dict]:
        """Run all tests and return results"""
        
        print(f"\n{'='*100}")
        print(f"🧪 VERSAILLES AGENT TEST SUITE")
        print(f"{'='*100}")
        print(f"Using LLM-as-a-Judge for evaluation")
        print(f"Test file: {self.test_queries_path}")
        
        # Load test queries
        test_queries = self.load_test_queries()
        if limit:
            test_queries = test_queries[:limit]
        
        print(f"Total test cases: {len(test_queries)}")
        print(f"{'='*100}\n")
        
        # Run tests
        for i, test_case in enumerate(test_queries):
            result = await self.test_single_query(test_case, i)
            self.results.append(result)
            
            # Brief pause between tests
            await asyncio.sleep(1)
        
        # Print summary
        self.print_summary()
        
        # Save results
        self.save_results()
        
        return self.results
    
    def print_summary(self):
        """Print test summary"""
        
        print(f"\n{'='*100}")
        print(f"📊 TEST SUMMARY")
        print(f"{'='*100}\n")
        
        if not self.results:
            print("No results to display")
            return
        
        # Calculate statistics
        total_tests = len(self.results)
        total_scores = [r['evaluation']['total_score'] for r in self.results]
        avg_score = sum(total_scores) / len(total_scores)
        avg_response_time = sum(r['response_time'] for r in self.results) / total_tests
        
        # Score distribution
        excellent = sum(1 for s in total_scores if s >= 9)
        good = sum(1 for s in total_scores if 7 <= s < 9)
        acceptable = sum(1 for s in total_scores if 5 <= s < 7)
        poor = sum(1 for s in total_scores if s < 5)
        
        print(f"Total Tests: {total_tests}")
        print(f"Average Score: {avg_score:.2f}/10")
        print(f"Average Response Time: {avg_response_time:.2f}s")
        print(f"\n📈 Score Distribution:")
        print(f"   Excellent (9-10): {excellent} ({excellent/total_tests*100:.1f}%)")
        print(f"   Good (7-8): {good} ({good/total_tests*100:.1f}%)")
        print(f"   Acceptable (5-6): {acceptable} ({acceptable/total_tests*100:.1f}%)")
        print(f"   Poor (0-4): {poor} ({poor/total_tests*100:.1f}%)")
        
        # Detailed scores by category
        accuracy_scores = [r['evaluation']['accuracy_score'] for r in self.results]
        completeness_scores = [r['evaluation']['completeness_score'] for r in self.results]
        relevance_scores = [r['evaluation']['relevance_score'] for r in self.results]
        helpfulness_scores = [r['evaluation']['helpfulness_score'] for r in self.results]
        
        print(f"\n📊 Average Scores by Category:")
        print(f"   Accuracy: {sum(accuracy_scores)/len(accuracy_scores):.2f}/3")
        print(f"   Completeness: {sum(completeness_scores)/len(completeness_scores):.2f}/3")
        print(f"   Relevance: {sum(relevance_scores)/len(relevance_scores):.2f}/2")
        print(f"   Helpfulness: {sum(helpfulness_scores)/len(helpfulness_scores):.2f}/2")
        
        # Best and worst performing queries
        best_result = max(self.results, key=lambda r: r['evaluation']['total_score'])
        worst_result = min(self.results, key=lambda r: r['evaluation']['total_score'])
        
        print(f"\n🏆 Best Performance:")
        print(f"   Test #{best_result['index']}: {best_result['evaluation']['total_score']}/10")
        print(f"   Question: {best_result['question'][:80]}...")
        
        print(f"\n⚠️  Worst Performance:")
        print(f"   Test #{worst_result['index']}: {worst_result['evaluation']['total_score']}/10")
        print(f"   Question: {worst_result['question'][:80]}...")
        
        print(f"\n{'='*100}\n")
    
    def save_results(self, output_file: str = None):
        """Save test results to JSON file"""
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"test_results_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.results),
                "results": self.results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Results saved to: {output_file}")


async def main():
    """Main test runner"""
    
    # Create tester
    tester = AgentTester()
    
    # Run all tests (or limit to first N tests for quick testing)
    await tester.run_all_tests(limit=2)  # Test first 2 queries for quick validation
    # await tester.run_all_tests()  # Test all queries
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
