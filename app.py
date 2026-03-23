import os
import sys
import json
import hashlib
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import requests

# Simple in-memory cache for analysis results
analysis_cache = {}

# Simple in-memory cache for OCR results
ocr_cache = {}

# Cache key generation function
def generate_cache_key(context, full_context):
    combined = f"{context}:{full_context}"
    return hashlib.md5(combined.encode()).hexdigest()

# OCR cache key generation function
def generate_ocr_cache_key(image_data, previous_context, next_context):
    combined = f"{image_data}:{previous_context}:{next_context}"
    return hashlib.md5(combined.encode()).hexdigest()

# Configuration
PORT = 8000

# Initialize Flask App
app = Flask(__name__, static_folder='principia/dist')
CORS(app)  # Enable CORS for all routes

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        context = data.get('context', '')
        full_context = data.get('fullContext', '')
        reasoning_config = data.get('reasoningConfig', {})
        vision_config = data.get('visionConfig', {})
        
        if not context:
            return jsonify({'error': 'No context provided'}), 400
        
        # Check cache first
        cache_key = generate_cache_key(context, full_context)
        if cache_key in analysis_cache:
            print(f"Cache hit for analysis")
            return jsonify(analysis_cache[cache_key])

        # Determine Client and Model for Reasoning (Explanation)
        if reasoning_config and reasoning_config.get('apiKey'):
            # print(f"Using custom reasoning config: {reasoning_config.get('model')}") # Removed for security
            current_reasoning_client = OpenAI(
                api_key=reasoning_config.get('apiKey'),
                base_url=reasoning_config.get('baseUrl')
            )
            current_reasoning_model = reasoning_config.get('model')
        else:
            return jsonify({'error': 'Reasoning API configuration missing. Please configure settings.'}), 401
            
        # 1. Get Explanation
        print(f"Requesting explanation...")
        explanation_prompt = f"""
        You are an expert physics and mathematics tutor.
        
        Target Formula/Concept: "{context}"
        
        Full Document Context:
        "{full_context}"
        
        Task:
        1. Analyze the "Target Formula/Concept" within the context of the "Full Document Context".
        2. Provide a brief, clear, and insightful explanation. Focus on the "why" and "how".
        3. **LANGUAGE DETECTION**: Detect the language used in the "Full Document Context" (e.g., English, Chinese, French). 
        4. **OUTPUT LANGUAGE**: Your explanation MUST be in the SAME language as the "Full Document Context". If the context is mixed, prioritize the language of the descriptive text surrounding the formula.
        5. **MATH RENDERING**: If your explanation includes mathematical formulas, YOU MUST wrap them in standard LaTeX math delimiters:
           - Use $...$ for inline math (e.g., $E=mc^2$).
           - Use $$...$$ for display math.
           - DO NOT use markdown code blocks for math.
        6. Return ONLY the explanation text.
        """
        
        explanation_response = current_reasoning_client.chat.completions.create(
            model=current_reasoning_model,
            messages=[
                {"role": "system", "content": "You are a helpful physics tutor."},
                {"role": "user", "content": explanation_prompt}
            ],
            temperature=0.3,
            top_p=0.9,
            timeout=30
        )
        explanation = explanation_response.choices[0].message.content.strip()

        # 2. Get Visualization Code
        # Use vision_config (Multimodal) for visualization if available, as it requires strong coding/spatial capabilities.
        if vision_config and vision_config.get('apiKey'):
            # print(f"Using custom vision config for visualization: {vision_config.get('model')}") # Removed for security
            viz_client = OpenAI(
                api_key=vision_config.get('apiKey'),
                base_url=vision_config.get('baseUrl')
            )
            viz_model = vision_config.get('model')
        else:
            return jsonify({'error': 'Vision API configuration missing. Please configure settings.'}), 401

        print(f"Requesting visualization...")
        viz_prompt = f"""
        You are an expert frontend developer and physics simulation specialist.
        
        Task: Create a **Dynamic, Interactive Physics Simulation** using HTML5 Canvas and JavaScript.
        
        **Source Material**:
        1. **Target Concept**: "{context}"
        2. **Physics Logic (Source of Truth for Formulas)**: 
           "{explanation}"
        3. **Scenario Context (Source of Truth for Environment/Parameters)**: 
           "{full_context}"
        
        **Implementation Strategy**:
        1. **Analyze the Physics**: Use the "Physics Logic" to determine the governing equations (kinematics, dynamics, wave equations, etc.).
        2. **Extract Parameters**: Scan the "Scenario Context" for specific values (e.g., "velocity of 20m/s", "angle of 45 degrees", "mass of 5kg"). 
           - **CRITICAL**: If the context mentions specific numbers, YOU MUST set them as the initial values for your simulation variables.
        3. **Design the Visuals**: Use the "Scenario Context" to decide what to draw (e.g., if it mentions a "cliff", draw a cliff; if "spring", draw a spring).
        
        CRITICAL REQUIREMENTS:
        1. **Relevance**: The simulation MUST directly visualize the specific physics concept described.
           - Use the context to understand specific scenarios.
           - If it's a projectile, show a projectile.
           - If it's a wave, show a wave.
           - If it's a field, show vector fields or particles in a field.
           - If it's a function, create a function graphing tool.
           - **DO NOT default to a pendulum or spring unless the concept specifically calls for it.**
        
        2. **Physics Accuracy**: Use `requestAnimationFrame` to animate the system based on real physics equations derived from the concept.
        
        3. **Interactivity**: 
           - Include HTML range sliders to adjust key parameters relevant to the specific model (e.g., initial velocity, charge, frequency, mass).
           - For function graphs, include input fields for function equations and parameter adjustments.
           - Provide play/pause/reset controls for simulations.
        
        4. **Style**: 
          - Background: Dark (`#000` or `#111`).
          - Text: Light (`#eee`).
          - Controls: Minimalist, styled for dark mode, with clear labels.
        
        5. **Advanced Features**:
           - For function graphs: Support multiple functions on the same graph with different colors.
           - For simulations: Include real-time data display (e.g., position, velocity, energy).
           - Add zoom and pan functionality for better exploration.
        
        6. **Language Adaptation**:
          - **LANGUAGE DETECTION**: Detect the language used in the "Full Document Context" (e.g., English, Chinese, French).
          - **OUTPUT LANGUAGE**: Any text displayed in the simulation (labels, titles, slider names, instructions) MUST be in the SAME language as the "Full Document Context". If the context is mixed, prioritize the language of the descriptive text surrounding the formula.

        7. **Output Format**:
          - Return **ONLY** the HTML snippet containing the container `div`, controls, and the `script` tag.
          - Do NOT include `<html>`, `<head>`, `<body>`, or markdown code fences.
          - The root container must have `width: 100%; height: 300px;`.
        """

        viz_response = viz_client.chat.completions.create(
            model=viz_model,
            messages=[
                {"role": "system", "content": "You are a code generator. Output raw HTML/JS only."},
                {"role": "user", "content": viz_prompt}
            ],
            temperature=0.2,
            top_p=0.85,
            timeout=45
        )
        visualization = viz_response.choices[0].message.content.strip()
        
        # Cleanup markdown if present
        if visualization.startswith("```html"):
            visualization = visualization[7:]
        if visualization.startswith("```"):
            visualization = visualization[3:]
        if visualization.endswith("```"):
            visualization = visualization[:-3]

        # Store in cache
        result = {
            "explanation": explanation,
            "visualization": visualization
        }
        analysis_cache[cache_key] = result
        print(f"Cache miss, stored new analysis result")
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in analyze: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert', methods=['POST'])
def convert_format():
    try:
        data = request.json
        content = data.get('content', '')
        target_format = data.get('targetFormat', 'tex') # 'tex' or 'md'
        reasoning_config = data.get('reasoningConfig', {})
        
        if not content:
            return jsonify({'error': 'No content provided'}), 400

        # Determine Client
        if reasoning_config and reasoning_config.get('apiKey'):
            # print(f"Using custom reasoning config for conversion: {reasoning_config.get('model')}") # Removed for security
            client = OpenAI(
                api_key=reasoning_config.get('apiKey'),
                base_url=reasoning_config.get('baseUrl')
            )
            model = reasoning_config.get('model')
        else:
             return jsonify({'error': 'Reasoning API configuration missing. Please configure settings.'}), 401

        print(f"Requesting format conversion to {target_format}...")
        
        if target_format == 'tex':
            prompt = f"""
            Convert the following Markdown/LaTeX mixed content into a pure, compile-ready LaTeX document body.
            
            Rules:
            1. Convert Markdown headers (#, ##) to LaTeX sections (\section, \subsection).
            2. Convert Markdown lists (- , 1.) to LaTeX lists (itemize, enumerate).
            3. Convert Markdown bold/italic to LaTeX (\textbf, \textit).
            4. **COLOR PRESERVATION**:
               - Keep `\textcolor{{color}}{{text}}` as is.
               - Convert `<font color="color">text</font>` to `\textcolor{{color}}{{text}}` (if present).
               - Convert `<span style="color: color">text</span>` to `\textcolor{{color}}{{text}}` (if present).
            5. Keep existing LaTeX math ($...$, $$...$$) unchanged.
            6. Return ONLY the converted LaTeX body code. Do NOT wrap in \documentclass.
            7. Do not include markdown code fences.
            
            Content:
            "{content}"
            """
        else: # md
            prompt = f"""
            Convert the following LaTeX content into clean Markdown.
            
            Rules:
            1. **COLOR PRESERVATION (HIGHEST PRIORITY)**: 
               - **KEEP** `\textcolor{{color}}{{text}}` commands AS IS. 
               - **DO NOT** convert color to bold (`**`) or italic (`*`).
               - **DO NOT** convert color to HTML.
               - Convert `{{\color{{color}} text}}` to `\textcolor{{color}}{{text}}`.
            2. Convert LaTeX sections (\section, \subsection) to Markdown headers (#, ##).
            3. Convert LaTeX lists to Markdown lists.
            4. Convert LaTeX text formatting (\textbf, \textit) to Markdown (**...**, *...*).
               - Only convert `\textbf` and `\textit`. DO NOT touch `\textcolor`.
            5. Keep LaTeX math ($...$, $$...$$) unchanged.
            6. Return ONLY the converted Markdown content.
            7. Do not include markdown code fences.
            
            Content:
            "{content}"
            """

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a document format converter."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            top_p=0.8,
            timeout=30
        )
        converted = response.choices[0].message.content.strip()
        
        # Cleanup
        if converted.startswith("```latex") or converted.startswith("```markdown"):
            converted = converted.split('\n', 1)[1]
        if converted.startswith("```"):
            converted = converted[3:]
        if converted.endswith("```"):
            converted = converted[:-3]

        return jsonify({'converted': converted.strip()})

    except Exception as e:
        print(f"Error in convert: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ocr', methods=['POST'])
def ocr():
    try:
        data = request.json
        image_data = data.get('image', '') # Expecting base64 string
        vision_config = data.get('visionConfig', {})
        previous_context = data.get('previousContext', '')
        next_context = data.get('nextContext', '')
        
        if not image_data:
            return jsonify({'error': 'No image provided'}), 400

        # Check cache first
        cache_key = generate_ocr_cache_key(image_data, previous_context, next_context)
        if cache_key in ocr_cache:
            print(f"Cache hit for OCR")
            return jsonify(ocr_cache[cache_key])

        # Determine Client and Model for Vision
        if vision_config and vision_config.get('apiKey'):
            # print(f"Using custom vision config: {vision_config.get('model')}") # Removed for security
            current_vision_client = OpenAI(
                api_key=vision_config.get('apiKey'),
                base_url=vision_config.get('baseUrl')
            )
            current_vision_model = vision_config.get('model')
        else:
            return jsonify({'error': 'Vision API configuration missing. Please configure settings.'}), 401

        # Construct Contextual Prompt
        system_prompt = """Transcribe this handwritten note into valid XeLaTeX code with high accuracy.

DETAILED RECOGNITION RULES:
1. **Content Extraction**: Capture ALL visible content, including handwritten text, printed text, mathematical formulas, symbols, diagrams, and annotations.
2. **LaTeX Formatting**: 
   - Return ONLY the body content (formulas, text, etc.).
   - Do NOT include \documentclass, \begin{document}, \maketitle, or \end{document}.
   - Assume standard packages (amsmath, amssymb, geometry, xcolor) are already loaded.
3. **Mathematical Formula Recognition**: 
   - Use standard LaTeX math mode ($...$ for inline, $$...$$ for display).
   - For complex formulas, use appropriate LaTeX environments (e.g., align, equation, cases).
   - Correctly identify and format mathematical symbols, operators, and functions.
   - Recognize subscripts and superscripts accurately (e.g., x_1, x^2, x_1^2).
   - For fractions, use \frac{numerator}{denominator} or \dfrac for display-style fractions.
   - For integrals, use proper LaTeX syntax (e.g., \int, \iint, \oint) with correct limits.
   - For vectors and matrices, use appropriate notation (e.g., \vec{v}, \mathbf{M}, \begin{matrix}).
   - For derivatives, use \frac{d}{dx} or \frac{\partial}{\partial x} as appropriate.
4. **Contextual Correction**: Correct any obvious physical or mathematical errors based on context, but preserve the original intent of the writing.
5. **Output Format**: Return ONLY the LaTeX code, no markdown fencing.
6. **COLOR DETECTION (ENHANCED)**: 
   - **Color Identification**: Carefully analyze the color of each handwritten stroke, considering both hue and intensity.
   - **Color Categories**: Recognize the following colors with high accuracy:
     * Red (\textcolor{red}{...})
     * Blue (\textcolor{blue}{...})
     * Green (\textcolor{green}{...})
     * Orange (\textcolor{orange}{...})
     * Purple (\textcolor{purple}{...})
     * Black (no color command)
     * Gray (no color command)
     * White (no color command)
   - **Color Consistency**: Apply color commands consistently to entire words, phrases, or formulas written in the same color.
   - **Mixed Colors**: If different parts of the same formula or text are in different colors, apply color commands to each part separately.
   - **Background Consideration**: Consider the background color when determining the text color (e.g., light text on dark background).
7. **Layout Preservation**: Maintain the original layout and structure of the content, including line breaks, indentation, and spacing.
8. **Symbol Recognition**: Accurately identify and transcribe special symbols, Greek letters, and mathematical notation.
9. **Handwriting Variations**: Account for different handwriting styles and variations in character formation.
10. **Context Integration**: Use the provided previous and next context to ensure accurate transcription and proper formatting.
"""

        
        if previous_context:
            system_prompt += f"\n\nPREVIOUS CONTEXT (The text immediately preceding this image):\n...{previous_context}\n\nINSTRUCTION: Ensure your transcription flows naturally from this previous context."
            
        if next_context:
            system_prompt += f"\n\nNEXT CONTEXT (The text immediately following this image):\n{next_context}...\n\nINSTRUCTION: Ensure your transcription connects smoothly to this next context."

        # Use Gemini/Custom for Vision/OCR as it has strong multimodal capabilities
        print(f"Requesting OCR with context...")
        response = current_vision_client.chat.completions.create(
            model=current_vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data
                            }
                        }
                    ],
                }
            ],
            max_tokens=2000,
            temperature=0.1,
            top_p=0.7,
            timeout=60
        )

        latex_code = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        if latex_code.startswith("```latex"):
            latex_code = latex_code[8:]
        if latex_code.startswith("```"):
            latex_code = latex_code[3:]
        if latex_code.endswith("```"):
            latex_code = latex_code[:-3]
            
        # Store in cache
        result = {'latex': latex_code.strip()}
        ocr_cache[cache_key] = result
        print(f"Cache miss, stored new OCR result")
            
        return jsonify(result)

    except Exception as e:
        print(f"Error in ocr: {e}")
        return jsonify({'error': str(e)}), 500

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
    print(f"--------------------------------------------------")
    print(f"The Principia Backend Running on Port {PORT}")
    print(f"--------------------------------------------------")
    app.run(port=PORT, debug=True, use_reloader=False)