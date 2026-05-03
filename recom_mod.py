from typing import List, Dict


# -----------------------------
# Data Type
# -----------------------------
User = Dict[str, any]


# -----------------------------
# Similarity Functions
# -----------------------------
def jaccard_similarity(list1: List[str], list2: List[str]) -> float:
    """
    Compute Jaccard similarity between two lists
    """
    set1, set2 = set(list1), set(list2)

    if not set1 and not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union


def calculate_similarity_score(user_a: User, user_b: User) -> float:
    """
    Calculate weighted similarity score between two users
    """
    weights = {
        "faculty": 2.0,
        "interests": 3.0,
        "hobbies": 2.0,
        "clubs": 3.0,
    }

    score = 0.0

    # Faculty match
    if user_a["faculty"] == user_b["faculty"]:
        score += weights["faculty"]

    # Interest similarity
    score += jaccard_similarity(user_a["interests"], user_b["interests"]) * weights["interests"]

    # Hobby similarity
    score += jaccard_similarity(user_a["hobbies"], user_b["hobbies"]) * weights["hobbies"]

    # Club similarity
    score += jaccard_similarity(user_a["clubs"], user_b["clubs"]) * weights["clubs"]

    return score


# -----------------------------
# Recommendation Engine
# -----------------------------
def recommend_users(current_user: User, all_users: List[User], limit: int = 5) -> List[User]:
    """
    Recommend top N similar users
    """
    scored_users = []

    for user in all_users:
        if user["id"] == current_user["id"]:
            continue  # Skip self

        score = calculate_similarity_score(current_user, user)
        scored_users.append((user, score))

    # Sort by score (descending)
    scored_users.sort(key=lambda x: x[1], reverse=True)

    # Return top N users
    return [user for user, _ in scored_users[:limit]]


# -----------------------------
# Example Data (Demo)
# -----------------------------
def load_sample_users() -> List[User]:
    """
    Sample dataset for testing
    """
    return [
        {
            "id": "1",
            "name": "Alice",
            "faculty": "FCI",
            "interests": ["coding", "ai", "gaming"],
            "hobbies": ["chess", "reading"],
            "clubs": ["robotics", "hackathon"]
        },
        {
            "id": "2",
            "name": "Bob",
            "faculty": "FCI",
            "interests": ["coding", "gaming"],
            "hobbies": ["chess"],
            "clubs": ["robotics"]
        },
        {
            "id": "3",
            "name": "Charlie",
            "faculty": "FOE",
            "interests": ["mechanics", "cars"],
            "hobbies": ["football"],
            "clubs": ["engineering"]
        },
        {
            "id": "4",
            "name": "Diana",
            "faculty": "FCI",
            "interests": ["ai", "data science"],
            "hobbies": ["reading"],
            "clubs": ["hackathon"]
        },
        {
            "id": "5",
            "name": "Ethan",
            "faculty": "FOM",
            "interests": ["business", "marketing"],
            "hobbies": ["networking"],
            "clubs": ["entrepreneur"]
        }
    ]


# -----------------------------
# Main Execution (Demo Run)
# -----------------------------
if __name__ == "__main__":
    users = load_sample_users()
    current_user = users[0]  # Alice

    recommendations = recommend_users(current_user, users, limit=3)

    print(f"Recommendations for {current_user['name']}:\n")

    for idx, user in enumerate(recommendations, start=1):
        print(f"{idx}. {user['name']} ({user['faculty']})")