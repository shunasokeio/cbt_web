from flask import Flask, render_template, request, jsonify, session
import os
import openai
from flask_cors import CORS
import time
import random
import logging
from dotenv import load_dotenv
from openai import APIConnectionError, APIError, APITimeoutError
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
CORS(app)



# --- CBT Prompt Logic (adapted from CBT3.ipynb) ---
def generate_cbt_prompt(cbt_step_question, user_answer, user_profile, past_conversation):
    system_prompt = (
        "You are an empathetic and helpful AI assistant designed to support Cognitive Behavioral Therapy (CBT). "
        "Your role is to analyze the user's responses and help facilitate the CBT process smoothly. "
        "Your objective is to guide the user in exploring their thoughts and feelings more concretely. "
        "For ambiguous answers, you will ask one concise, clarifying question and present options for the user to choose from; for specific answers, you will summarize to confirm understanding."
    )
    prompt_template = """
                      # Instructions

                      Please evaluate the user's answer below.

                      1.  **If the answer is ambiguous:**
                          * Generate one relevant follow-up question to help the user delve deeper.
                          * Provide three multiple-choice options for that question. Options should be as short and concise as possible.
                          * Personalize the question and options using the provided [User's Basic Information] and [Relevant Past Conversation].
                          * Output the response in JSON format with the keys: `\"type\": \"follow-up\"`, `\"question\": \"your_generated_question\"`, and `\"options\": [\"option1\", \"option2\", \"option3\"]`.

                      2.  **If the answer is sufficiently specific:**
                          * Provide a concise summary of the user's response.
                          * Output the response in JSON format with the keys: `\"type\": \"summary\"` and `\"summary\": \"your_generated_summary\"`.

                      # Context

                      ### Initial CBT Step Question
                      {cbt_question}

                      ### User's Answer
                      {user_answer}

                      ### User's Basic Information
                      {profile}

                      ### Relevant Past Conversation
                      {history}

                      # Your Response (in JSON format)
                      """
    user_prompt = prompt_template.format(
        cbt_question=cbt_step_question,
        user_answer=user_answer,
        profile=user_profile,
        history=past_conversation,
    )
    return system_prompt, user_prompt

def call_gpt(model: str, prompt: str, sys_prompt: str, api_key: str) -> str:
    client = openai.OpenAI(api_key=api_key)
    max_retries = 5
    delay = 2
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except (APIConnectionError, APIError, APITimeoutError) as e:
            logging.warning(f"OpenAI API error: {e}. Retrying in {delay:.1f} seconds...")
            time.sleep(delay * (1 + random.random()))
            delay *= 2
        except Exception as e:
            raise e
    raise Exception("Failed to get response from OpenAI API after multiple retries.")

@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/chat')
def chat_page():
    return render_template('chat.html', 
                         chat_title="CBT Step 1: Identify the Situation",
                         initial_question="What specific situation or event is causing you stress today?")

@app.route('/chat/step1')
def chat_step1():
    return render_template('chat.html', 
                         chat_title="CBT Step 1: Identify the Situation",
                         initial_question="What specific situation or event is causing you stress today?")

@app.route('/chat/step2')
def chat_step2():
    return render_template('chat.html', 
                         chat_title="CBT Step 2: Identify the Feelings",
                         initial_question="What emotions are you experiencing right now? How intense are they on a scale of 1-10?")

@app.route('/chat/step3')
def chat_step3():
    return render_template('chat.html', 
                         chat_title="CBT Step 3: Identify the Thoughts",
                         initial_question="What thoughts are going through your mind about this situation? What are you telling yourself?")

@app.route('/chat/step4')
def chat_step4():
    return render_template('chat.html', 
                         chat_title="CBT Step 4: Identify the Thought Distortion",
                         initial_question="Can you identify any thinking patterns that might be distorted? (e.g., all-or-nothing thinking, catastrophizing)")

@app.route('/chat/step5')
def chat_step5():
    return render_template('chat.html', 
                         chat_title="CBT Step 5: Revised Thinking & Next Action",
                         initial_question="What would be a more balanced way to think about this situation? What constructive action can you take?")

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message', '')
    step = data.get('step', 1)  # Default to step 1 if not provided

    # Initialize or update conversation history in session
    if 'user_history' not in session:
        session['user_history'] = []
    session['user_history'].append(user_input)
    session.modified = True  # Ensure session is saved

    # Define CBT questions and context for each step
    cbt_questions = {
        1: "What specific situation or event is causing you stress today?",
        2: "What emotions are you experiencing right now? How intense are they on a scale of 1-10?",
        3: "What thoughts are going through your mind about this situation? What are you telling yourself?",
        4: "Can you identify any thinking patterns that might be distorted? (e.g., all-or-nothing thinking, catastrophizing)",
        5: "What would be a more balanced way to think about this situation? What constructive action can you take?"
    }
    
    # Define step-specific system prompts
    step_system_prompts = {
        1: "You are an empathetic CBT assistant helping the user identify the specific situation causing their stress. Focus on getting concrete details about what happened, when, where, and with whom.",
        2: "You are an empathetic CBT assistant helping the user identify and rate their emotions. Help them name specific feelings and assess their intensity on a scale of 1-10.",
        3: "You are an empathetic CBT assistant helping the user identify their automatic thoughts about the situation. Help them recognize what they're telling themselves and any assumptions they're making.",
        4: "You are an empathetic CBT assistant helping the user identify cognitive distortions in their thinking. Look for patterns like all-or-nothing thinking, catastrophizing, overgeneralization, personalization, etc.",
        5: "You are an empathetic CBT assistant helping the user develop more balanced thoughts and constructive actions. Help them challenge distorted thinking and create realistic, helpful perspectives."
    }

    cbt_question = cbt_questions.get(step, cbt_questions[1])
    user_profile = ""
    # Join all previous user answers (except the current one) for context
    past_conversation = " -> ".join(session['user_history'][:-1]) if len(session['user_history']) > 1 else ""

    api_key = os.environ.get('OPENAI_API_KEY', '')
    model = 'gpt-4o'  # or 'gpt-3.5-turbo' if available
    
    # Use step-specific system prompt
    system_prompt = step_system_prompts.get(step, step_system_prompts[1])
    user_prompt = f"""
    # Instructions

    Please evaluate the user's answer below for CBT Step {step}.

    1.  **If the answer is ambiguous:**
        * Generate one, concise, relevant follow-up question to help the user delve deeper into this specific CBT step.
        * Provide three multiple-choice options for that question.
        * The options must be short, direct answers to the follow-up question, not additional questions.
        * Do NOT make the options questions themselves.
        * Personalize the question and options using the provided [User's Basic Information] and [Relevant Past Conversation].
        * Output the response in JSON format with the keys: `"type": "follow-up"`, `"question": "your_generated_question"`, and `"options": ["option1", "option2", "option3"]`.
"""
    
    try:
        print(f"requesting API for step {step}")
        ai_response = call_gpt(model, user_prompt, system_prompt, api_key)
        print(ai_response)
        return jsonify({'response': ai_response})
    except Exception as e:
        return jsonify({'response': f"Sorry, there was an error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True) 