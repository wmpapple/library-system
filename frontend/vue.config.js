const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  lintOnSave: false,
  // --- 添加以下配置 ---
  pages: {
    index: {
      entry: 'src/main.js',
      title: '图书管理系统 | LMS', // 在这里修改标题
    },
  },
  devServer: {
    client: {
      overlay: {
        runtimeErrors: (error) => {
          if (error.message.includes('ResizeObserver loop completed with undelivered notifications')) {
            return false;
          }
          return true;
        },
      },
    },
  },
})
