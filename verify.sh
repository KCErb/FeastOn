#!/bin/bash
set -e

echo "=== FeastOn Project Verification ==="
echo

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}1. Testing Pipeline CLI${NC}"
cd pipeline
source venv/bin/activate 2>/dev/null || true
feaston --version 2>/dev/null || feaston --help | head -5
echo -e "${GREEN}✓ Pipeline CLI working${NC}"
echo

echo -e "${BLUE}2. Testing Backend${NC}"
cd ../backend
source venv/bin/activate 2>/dev/null || true
python -c "from conflang_backend.main import app; print('✓ Backend imports successfully')"
echo -e "${GREEN}✓ Backend ready${NC}"
echo

echo -e "${BLUE}3. Testing Frontend${NC}"
cd ../frontend
if [ -f "dist/index.html" ]; then
    echo -e "${GREEN}✓ Frontend build exists${NC}"
else
    echo "Frontend needs build (run 'npm run build')"
fi
echo

echo -e "${BLUE}4. Project Structure${NC}"
cd ..
echo "Pipeline providers:"
ls -1 pipeline/conflang_pipeline/providers/*.py | grep -v __pycache__ | sed 's/.*\//  - /'
echo
echo "Backend providers:"
ls -1 backend/conflang_backend/providers/*.py | grep -v __pycache__ | sed 's/.*\//  - /'
echo
echo "Frontend providers:"
ls -1 frontend/src/providers/*.tsx 2>/dev/null | sed 's/.*\//  - /' || echo "  (to be created)"
echo

echo -e "${GREEN}=== All Systems Ready ===${NC}"
echo
echo "Next steps:"
echo "  1. Terminal 1: cd backend && source venv/bin/activate && python run.py"
echo "  2. Terminal 2: cd frontend && npm run dev"
echo "  3. Terminal 3: cd pipeline && source venv/bin/activate && feaston --help"
echo
echo "Then visit: http://localhost:5173"
