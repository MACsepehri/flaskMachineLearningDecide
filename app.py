from flask import Flask, render_template, redirect, request, session
import ast
from collections import Counter

app = Flask(__name__)
app.secret_key = "my_secret_key"

def is_valid_python_list(input_string):
    try:
        parsed = ast.literal_eval(input_string.strip())
        if isinstance(parsed, list):
            return True, parsed
        else:
            return False, None
    except (ValueError, SyntaxError, TypeError):
        return False, None

def find_similarities(base_data, lists_data):
    if not lists_data:
        return {
            'similarities': [],
            'total_lists': 0,
            'summary': 'No lists to compare'
        }
    
    similarities = []
    
    for idx, lst in enumerate(lists_data):
        if isinstance(base_data, list):
            base_set = set(base_data)
            list_set = set(lst)
            
            is_subset = list_set.issubset(base_set)
            common_elements = list(base_set.intersection(list_set))
            common_count = len(common_elements)
            
            if is_subset:
                similarity_score = 100.0
            elif common_count > 0:
                similarity_score = (common_count / len(lst)) * 100 if len(lst) > 0 else 0
            else:
                similarity_score = 0
            
            not_in_base = [elem for elem in lst if elem not in base_data]
            missing_from_base = [elem for elem in base_data if elem not in lst]
            all_in_base = all(elem in base_data for elem in lst)
            
            similarities.append({
                'list_index': idx + 1,
                'list': lst,
                'common_elements': common_elements,
                'common_count': common_count,
                'is_subset': is_subset,
                'all_in_base': all_in_base,
                'not_in_base': not_in_base,
                'missing_from_base': missing_from_base[:5],
                'similarity_score': round(similarity_score, 2),
                'length': len(lst),
                'base_length': len(base_data)
            })
        else:
            contains_base = base_data in lst if isinstance(base_data, (int, float, str)) else False
            count_base_in_list = lst.count(base_data) if base_data in lst else 0
            
            similar_elements = []
            if isinstance(base_data, int):
                similar_elements = [x for x in lst if isinstance(x, int) and x != base_data]
            elif isinstance(base_data, float):
                similar_elements = [x for x in lst if isinstance(x, (int, float)) and x != base_data]
            elif isinstance(base_data, str):
                similar_elements = [x for x in lst if isinstance(x, str) and x != base_data]
            
            similarity_score = 0
            if len(lst) > 0:
                if contains_base:
                    similarity_score = 1.0 / len(lst)
                if similar_elements:
                    similarity_score += len(similar_elements) / len(lst)
                similarity_score = min(similarity_score, 1.0) * 100
            
            similarities.append({
                'list_index': idx + 1,
                'list': lst,
                'contains_base': contains_base,
                'count_base_in_list': count_base_in_list,
                'similar_elements': similar_elements,
                'similarity_score': round(similarity_score, 2),
                'length': len(lst)
            })
    
    best_match = None
    if similarities:
        best_match = max(similarities, key=lambda x: x['similarity_score'])
        if best_match['similarity_score'] == 0:
            best_match = None
    
    total_lists = len(lists_data)
    
    if isinstance(base_data, list):
        lists_fully_matching = sum(1 for s in similarities if s['is_subset'])
        avg_similarity = sum(s['similarity_score'] for s in similarities) / total_lists if total_lists > 0 else 0
        
        return {
            'similarities': similarities,
            'total_lists': total_lists,
            'lists_fully_matching': lists_fully_matching,
            'avg_similarity': round(avg_similarity, 2),
            'best_match': best_match,
            'summary': f"{lists_fully_matching} out of {total_lists} lists are subsets of the base data",
            'is_list_base': True
        }
    else:
        lists_with_base = sum(1 for s in similarities if s['contains_base'])
        avg_similarity = sum(s['similarity_score'] for s in similarities) / total_lists if total_lists > 0 else 0
        
        return {
            'similarities': similarities,
            'total_lists': total_lists,
            'lists_with_base': lists_with_base,
            'lists_without_base': total_lists - lists_with_base,
            'avg_similarity': round(avg_similarity, 2),
            'best_match': best_match,
            'summary': f"Found {lists_with_base} out of {total_lists} lists containing the base data",
            'is_list_base': False
        }

def find_common_patterns(lists_data):
    if not lists_data:
        return {'common_elements': [], 'frequency': {}}
    
    all_elements = []
    for lst in lists_data:
        all_elements.extend(lst)
    
    frequency = Counter(all_elements)
    
    if len(lists_data) > 0:
        common_elements = []
        for element, count in frequency.items():
            if all(element in lst for lst in lists_data):
                common_elements.append(element)
    
    return {
        'common_elements': common_elements,
        'frequency': dict(frequency.most_common()),
        'total_elements': len(all_elements),
        'unique_elements': len(frequency)
    }

@app.route("/")
def index():
    if "history" not in session:
        session["history"] = []
    if "base_data" not in session:
        session["base_data"] = None
    if "similarity_results" not in session:
        session["similarity_results"] = None
    
    if session.get("base_data") is not None and session.get("history"):
        base_data = session["base_data"]
        lists_data = session["history"]
        session["similarity_results"] = find_similarities(base_data, lists_data)
        session["common_patterns"] = find_common_patterns(lists_data)
        session.modified = True
    
    return render_template("index.html", session=session)

@app.route("/send", methods=["POST"])
def send():
    query = request.form.get("query")
    
    if not query or query.strip() == "":
        return redirect("/")
    
    if session.get("base_data") is None:
        try:
            if query.strip().startswith('[') and query.strip().endswith(']'):
                try:
                    parsed = ast.literal_eval(query.strip())
                    if isinstance(parsed, list):
                        session["base_data"] = parsed
                        session.modified = True
                        return redirect("/")
                except:
                    pass
            
            if query.strip().isdigit():
                base_value = int(query.strip())
            elif query.strip().replace('.', '').isdigit():
                base_value = float(query.strip())
            else:
                base_value = query.strip()
            
            session["base_data"] = base_value
            session.modified = True
            return redirect("/")
        except Exception:
            return redirect("/")
    else:
        is_valid, parsed_list = is_valid_python_list(query)
        
        if not is_valid:
            return redirect("/")
        
        try:
            history = session.get("history", [])
            history.append(parsed_list)
            session["history"] = history
            session.modified = True
        except Exception:
            return redirect("/")
        
        return redirect("/")

@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
