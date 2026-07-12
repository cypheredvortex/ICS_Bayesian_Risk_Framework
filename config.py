"""
config.py

Shared constants and lookup tables. Kept separate so tuning the model
(e.g. adjusting how much a firewall discounts an edge, or how phishable
a role is) never requires touching logic files.
"""

# --- Phase 2: edge weights ---
W0 = {
    "controls": 0.70,
    "monitors": 0.20,
    "actuates": 0.60,
    "connects-to": 0.50,
    "programs / operates": 0.80,
}

M_FIREWALL = {
    True: 0.30,   # firewalled
    False: 1.00,  # not firewalled
}

# --- Phase 3A: base probabilities ---
M_EXPOSURE = {
    True: 1.3,   # exposed
    False: 0.3,  # not exposed
}

M_PATCH = {
    False: 1.2,  # not patched
    True: 0.9,   # patched
}

R_PHISHING = {
    "operator": 0.35,
    "engineer": 0.20,
    "admin": 0.15,
    "guest": 0.50,
}

M_PRIVILEGE = {
    "standard": 1.0,
    "elevated": 1.3,
    "admin": 1.5,
}

P_BASE_CAP = 0.95