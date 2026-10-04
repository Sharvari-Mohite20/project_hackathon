import re
from datetime import datetime, timedelta

# Common English and domain-specific stopwords
STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t', 
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 
    'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from', 
    'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 
    'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'me', 'more', 'most', 
    'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours', 
    'ourselves', 'out', 'over', 'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than', 'that', 
    'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 
    'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasn\'t', 'we', 'were', 'what', 
    'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'with', 'would', 'you', 'your', 'yours',
    'item', 'lost', 'found', 'please', 'help', 'someone', 'somewhere'
}

def tokenize(text):
    """Clean and tokenize text into lowercase alphanumeric keywords excluding stopwords."""
    if not text:
        return set()
    words = re.findall(r'\b[a-zA-Z0-9_]{3,}\b', text.lower())
    return {w for w in words if w not in STOPWORDS}


def calculate_match_score(item_a, item_b):
    """
    Calculate similarity score between two items (one lost, one found).
    Returns (score_percentage, reasons_list).
    """
    # They must be opposite types (one lost, one found)
    if item_a.item_type == item_b.item_type:
        return 0, []
    
    score = 0
    reasons = []
    
    # 1. Category Matching (Weight: 30%)
    if item_a.category.lower() == item_b.category.lower():
        score += 30
        reasons.append(f"Category matched: {item_a.category}")
    else:
        # If categories differ completely, maximum possible score is heavily reduced
        return 0, []
        
    # 2. Keyword & Title Overlap (Weight: 40%)
    title_a_tokens = tokenize(item_a.title)
    title_b_tokens = tokenize(item_b.title)
    desc_a_tokens = tokenize(item_a.description)
    desc_b_tokens = tokenize(item_b.description)
    
    all_a_tokens = title_a_tokens.union(desc_a_tokens)
    all_b_tokens = title_b_tokens.union(desc_b_tokens)
    
    # Title tokens overlap is weighted higher
    title_overlap = title_a_tokens.intersection(title_b_tokens)
    general_overlap = all_a_tokens.intersection(all_b_tokens)
    
    if title_overlap:
        score += min(25, len(title_overlap) * 12)
        reasons.append(f"Matching title words: {', '.join(title_overlap)}")
    
    remaining_overlap = general_overlap - title_overlap
    if remaining_overlap:
        score += min(15, len(remaining_overlap) * 5)
        reasons.append(f"Shared keywords: {', '.join(list(remaining_overlap)[:4])}")
        
    # 3. Location Matching (Weight: 20%)
    if item_a.location_id and item_b.location_id:
        if item_a.location_id == item_b.location_id:
            score += 20
            loc_name = item_a.location.name if item_a.location else "Same location"
            reasons.append(f"Identical campus location: {loc_name}")
        elif item_a.location and item_b.location and item_a.location.zone == item_b.location.zone:
            score += 10
            reasons.append(f"Same campus zone: {item_a.location.zone}")
    elif item_a.specific_location and item_b.specific_location:
        # Check text overlap in specific location
        loc_a_tokens = tokenize(item_a.specific_location)
        loc_b_tokens = tokenize(item_b.specific_location)
        loc_overlap = loc_a_tokens.intersection(loc_b_tokens)
        if loc_overlap:
            score += 15
            reasons.append(f"Matching location clues: {', '.join(loc_overlap)}")

    # 4. Date Proximity (Weight: 10%)
    if item_a.date_lost_or_found and item_b.date_lost_or_found:
        days_diff = abs((item_a.date_lost_or_found - item_b.date_lost_or_found).days)
        if days_diff <= 2:
            score += 10
            reasons.append(f"Reported within {days_diff} day(s)")
        elif days_diff <= 7:
            score += 5
            reasons.append(f"Reported within a week ({days_diff} days apart)")
            
    final_score = min(100, score)
    return final_score, reasons


def find_potential_matches(target_item, candidate_items, min_score=35):
    """
    Given a target item and a list of candidate items,
    returns a sorted list of dicts with matching item and details.
    """
    matches = []
    for candidate in candidate_items:
        if candidate.id == target_item.id:
            continue
        if candidate.status in ['resolved', 'closed']:
            continue
            
        score, reasons = calculate_match_score(target_item, candidate)
        if score >= min_score:
            matches.append({
                'item': candidate,
                'score': score,
                'reasons': reasons
            })
            
    # Sort highest match score first
    matches.sort(key=lambda m: m['score'], reverse=True)
    return matches
