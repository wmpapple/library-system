pip install -r .\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
npm install @vue/composition-api --save-dev

# frontend
conda activate dbs
cd frontend
npm run serve


# backend
conda activate dbs
uvicorn backend.app.main:app --reload