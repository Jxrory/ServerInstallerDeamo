### 直接在远程执行本地脚本

流式执行安装：不需要上传文件

```bash
# 远程安装git server
ssh my-server 'bash -s' < GitServerInstaller/install.s

# 在远程创建裸仓
ssh my-server 'create-repo UniChat'
```