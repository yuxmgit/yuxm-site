// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: false },

  modules: ['@nuxt/content', '@nuxtjs/tailwindcss'],

  // 内容配置（@nuxt/content v3）：集合定义见 content.config.ts
  content: {
    build: {
      markdown: {
        // TOC 需包含 h2/h3（默认 depth 为 2）
        toc: { depth: 3 },
        highlight: {
          theme: {
            default: 'github-light',
            dark: 'github-dark'
          },
          // v3 中显式指定 langs 会覆盖默认列表，故需包含默认语言
          langs: [
            'js', 'jsx', 'json', 'ts', 'tsx', 'vue', 'css', 'html', 'bash',
            'md', 'mdc', 'yaml',
            'shell', 'yml', 'sql', 'docker', 'dockerfile', 'python',
            'javascript', 'typescript', 'nginx', 'ini', 'toml', 'markdown',
            'c', 'go', 'diff'
          ]
        }
      }
    }
  },

  runtimeConfig: {
    // 服务端专用密钥（Nitro server routes 中使用），由环境变量覆盖
    oauthGithubSecret: '',
    oauthGiteeSecret: '',
    public: {
      // FastAPI 后端地址
      apiBase: 'http://localhost:8000',
      siteName: '虞先森的技术站',
      githubUrl: 'https://github.com/yuxiangming',
      giteeUrl: 'https://gitee.com/yuxiangming'
    }
  },

  css: ['~/assets/css/main.css'],

  app: {
    head: {
      htmlAttrs: { lang: 'zh-CN' },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' }
      ]
    }
  }
})
