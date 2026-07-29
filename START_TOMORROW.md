# 明天启动项目

双击或在终端运行：

```powershell
D:\jay_demo\vae_demo\start-local.cmd
```

脚本会依次启动 PostgreSQL、Redis、独立 BGE 推理服务、后端和前端，并等待健康检查通过。

启动完成后访问：

```text
http://127.0.0.1:5173
```

遇到问题时运行：

```powershell
D:\jay_demo\vae_demo\check-local.cmd
```

日志位于 `D:\jay_demo\vae_demo\.runtime`。停止本地应用进程可运行：

```powershell
D:\jay_demo\vae_demo\stop-local.cmd
```
