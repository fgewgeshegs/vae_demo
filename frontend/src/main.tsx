import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ConfigProvider
    locale={zhCN}
    theme={{
      algorithm: theme.defaultAlgorithm,
      token: {
        colorPrimary: '#2563eb',
        colorPrimaryHover: '#1d4ed8',
        colorBgContainer: '#ffffff',
        colorBgElevated: '#ffffff',
        colorBorder: '#e2e8f0',
        colorBorderSecondary: '#f1f5f9',
        borderRadius: 6,
        fontSize: 14,
        controlHeight: 36,
        fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      },
      components: {
        Card: { colorBorderSecondary: '#e2e8f0' },
        Menu: {
          colorItemBgHover: '#eff6ff',
          colorItemTextSelected: '#2563eb',
          colorItemBgSelected: '#eff6ff',
        },
        Button: { primaryShadow: 'none', controlHeight: 34, fontSize: 13, borderRadius: 6 },
        Tag: { borderRadius: 4, fontSize: 11 },
        Progress: { borderRadius: 4 },
      },
    }}
  >
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </ConfigProvider>
)