# Production Readiness Implementation Progress

## Step 1: Fix Auth Router Issues
- [x] Fix `require_permission("admin:*")` → use `require_admin` dependency
- [x] Add `expires_in` to LoginResponse
- [x] Update `/me` to return `UserMeResponse` with role_name and permissions
- [x] Fix `change_password` to use `PasswordChangeRequest` schema
- [x] Add `/users/me/change-password` for self-service

## Step 2: Add RBAC to All GRC Routers
- [x] compliance.py — `require_module_access("compliance")` on all endpoints
- [x] capa.py — `require_module_access("capa")` on all endpoints
- [x] controls.py — `require_module_access("controls")` on all endpoints
- [x] risk.py — `require_module_access("risk")` on all endpoints
- [x] audit_management.py — `require_module_access("audit")` on all endpoints
- [x] assets.py — `require_module_access("assets")` on all endpoints
- [x] threats.py — `require_module_access("threats")` on all endpoints (incl. actor endpoints restored)
- [x] vulnerabilities.py — `require_module_access("vulnerabilities")` on all endpoints
- [x] zones.py — `require_module_access("zones")` on all endpoints
- [x] organizations.py — `require_module_access("organizations")` on all endpoints
- [x] security.py — added `zones` module to MODULE_ACTIONS + `require_admin` helper

## Step 3: Frontend Auth Integration
- [x] Create authStore.tsx — JWT persistence, login/logout, /me profile, authHeader
- [x] Update grc.ts API client with auth headers (setAuthHeader)
- [x] Create LoginPage.tsx
- [x] Update App.tsx — auth guard wrapper + authenticated app component (fixes Rules of Hooks)
- [x] Update main.tsx — wrap App in AuthProvider
- [x] Update Layout.tsx — user footer with role display + sign out

## Step 4: Tests
- [x] Auth tests — login, /me, self-service password change, wrong password
- [x] RBAC tests — read allowed / write denied per role across modules

## Step 5: Verification
- [x] Run tests — **103 passed** (18 new auth/RBAC tests + 85 existing)
- [x] Build frontend — `npm run build` succeeded (tsc -b && vite build)

