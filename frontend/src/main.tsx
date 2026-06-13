import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#6366f1',
          colorPrimaryHover: '#818cf8',
          colorBgContainer: '#141b2d',
          colorBgElevated: '#1a2237',
          colorBgLayout: '#0a0e1a',
          colorText: 'rgba(255, 255, 255, 0.90)',
          colorTextSecondary: 'rgba(255, 255, 255, 0.60)',
          borderRadius: 8,
          fontSize: 14,
          colorBorder: 'rgba(255, 255, 255, 0.08)',
          controlOutline: 'rgba(99, 102, 241, 0.25)',
        },
        components: {
          Button: {
            colorPrimary: '#6366f1',
            colorPrimaryHover: '#818cf8',
            primaryShadow: '0 0 20px rgba(99, 102, 241, 0.35)',
            borderRadius: 8,
          },
          Menu: {
            colorItemBg: 'transparent',
            colorItemBgHover: 'rgba(255, 255, 255, 0.06)',
            colorItemBgSelected: 'rgba(99, 102, 241, 0.15)',
            colorItemText: 'rgba(255, 255, 255, 0.60)',
            colorItemTextHover: 'rgba(255, 255, 255, 0.90)',
            colorItemTextSelected: '#818cf8',
            itemBorderRadius: 8,
            itemMarginInline: 8,
          },
          Card: {
            colorBgContainer: 'rgba(255, 255, 255, 0.04)',
            colorBorderSecondary: 'rgba(255, 255, 255, 0.08)',
          },
          Progress: {
            defaultColor: '#6366f1',
          },
          Input: {
            colorBgContainer: 'rgba(255, 255, 255, 0.06)',
            colorBorder: 'rgba(255, 255, 255, 0.10)',
            colorPrimaryHover: '#818cf8',
            colorPrimary: '#6366f1',
          },
          Modal: {
            colorBgContainer: '#141b2d',
          },
          Table: {
            colorBgContainer: 'transparent',
            borderColor: 'rgba(255, 255, 255, 0.08)',
            headerColor: 'rgba(255, 255, 255, 0.60)',
            headerBg: 'rgba(255, 255, 255, 0.03)',
            rowHoverBg: 'rgba(255, 255, 255, 0.04)',
          },
        },
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>
)
