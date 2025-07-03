from flask import Flask, request, jsonify
from sympy import (
    symbols, Eq, solve, simplify, expand, factor, sympify,
    diff, integrate, sin, cos, tan, log as sym_log, sqrt
)
from openai import OpenAI
import os
import re

# ————— Configuración de OpenAI —————
os.environ["OPENAI_API_KEY"] = "REMOVIDO...pon-tu-clave..."
client = OpenAI()

app = Flask(__name__)

@app.route('/solve', methods=['POST'])
def solve_problem():
    data = request.get_json(force=True)
    problem = data.get("problem", "").strip()
    x = symbols('x')
    steps = []

    if not problem:
        return jsonify({"error": "No se recibió el campo 'problem'"}), 400

    try:
        # ——— Detectar ecuación vs expresión
        if '=' in problem:
            left, right = problem.split('=', 1)
            left_expr = sympify(left)
            right_expr = sympify(right)
            equation = Eq(left_expr, right_expr)
            solution = solve(equation, x)

            steps.append(f"1) Ecuación: {problem}")
            steps.append(f"2) Forma simbólica: {equation}")
            steps.append(f"3) Movemos todo a un lado: {Eq(left_expr-right_expr, 0)}")
            steps.append(f"4) Simplificamos: {simplify(left_expr-right_expr)} = 0")
            steps.append(f"5) Despejamos x usando solve(): {solution}")

            ai_expl = get_ai_explanation(problem, solution, "equation")
            return jsonify({
                "type": "equation",
                "equation": problem,
                "solution": str(solution),
                "steps": steps,
                "ai_explanation": ai_expl
            })

        # ——— Procesar expresión
        expr = sympify(problem)
        steps.append(f"1) Expresión inicial: {problem}")

        # Expandir
        expnd = expand(expr)
        if expnd != expr:
            steps.append(f"2) Expandimos: {expnd}")
        else:
            steps.append("2) No hay productos ni potencias que expandir.")

        # Factorizar
        fct = factor(expnd)
        if fct != expnd:
            steps.append(f"3) Factorizamos: {fct}")
        else:
            steps.append("3) No fue posible factorizar.")

        # Simplificar
        simp = simplify(fct)
        steps.append(f"4) Simplificamos: {simp}")

        # Evaluar numéricamente
        try:
            val = simp.evalf()
            steps.append(f"5) Evaluamos numéricamente: {val}")
        except:
            steps.append("5) No pudo evaluarse numéricamente sin valores concretos.")

        ai_expl = get_ai_explanation(problem, simp, "expression")
        return jsonify({
            "type": "expression",
            "original": problem,
            "simplified": str(simp),
            "evaluated": str(simp.evalf()),
            "steps": steps,
            "ai_explanation": ai_expl
        })

    except Exception as e:
        return jsonify({"error": f"Error al procesar: {e}"}), 400


def get_ai_explanation(problem, solution, type_):
    prompt = (
        f"Eres un profesor de matemáticas muy claro. "
        f"Explica paso a paso cómo resolver este problema:\n"
        f"Tipo: {type_}\nProblema: {problem}\nSolución: {solution}\n"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return resp.choices[0].message.content
    except Exception:
        # Aquí luego podrías llamar otra IA como LLaMa, Cohere, Google PaLM, etc
        return fallback_manual(problem, solution, type_)


def fallback_manual(problem, solution, type_):
    text = ""
    if type_ == "equation":
        text += f"1) Planteamos la ecuación: {problem}\n"
        if re.search(r"[a-z]\*\*[2]", problem) or "x^2" in problem:
            text += "2) Es cuadrática (término x²).\n"
            text += "3) Movemos todo a un lado y simplificamos.\n"
            text += "4) Aplicamos fórmula general: x = [-b ± √(b²-4ac)]/(2a).\n"
            text += f"5) Resultado: {solution}\n"
        else:
            text += "2) Es lineal.\n"
            text += "3) Aislamos x.\n"
            text += f"4) Resultado: x = {solution}\n"
        return text + "6) ¡Problema resuelto!"
    text += f"1) Iniciamos con: {problem}\n"
    if re.search(r"\+|\-", problem): text += "2) Sumamos/restamos términos semejantes.\n"
    if "*" in problem or "**" in problem: text += "3) Aplicamos potencias/productos.\n"
    if "log" in problem: text += "4) Usamos propiedades logarítmicas.\n"
    if re.search(r"\b(sin|cos|tan)\b", problem): text += "4) Identidades trigonométricas.\n"
    text += f"5) Simplificación final: {solution}\n"
    return text + "6) ¡Explicación completa!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
