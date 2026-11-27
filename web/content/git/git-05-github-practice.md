---
title: "第 05 章 实战：创建你的 GitHub 练习仓库"
description: "难度：★★☆　预计耗时：90 分钟 本章目标：在 GitHub 上从零创建一个专属练习仓库 git-practice，把前三章学的命令全部实打实跑一遍——建分支、两种合并、模拟发"
category: git
series: git-in-action
seriesOrder: 5
tags: ["Git", "GitHub", "实战"]
date: 2026-11-27
sourceRepo: https://github.com/yuxiangming/git-practice
---

> 难度：★★☆　预计耗时：90 分钟
> 本章目标：在 GitHub 上从零创建一个专属练习仓库 git-practice，把前三章学的命令全部实打实跑一遍——建分支、两种合并、模拟发布、发起 PR。这个仓库就是你的 Git 游乐场，练坏了随时推倒重来。

---

## 一、为什么专门开一个仓库练

Git 是肌肉记忆型技能：看得懂 ≠ 敲得对。真实项目里不敢乱试（手一抖 push 错了可能就是事故），所以需要一个**零风险、随便玩**的练习仓库：

- 练坏了可以整个删掉重建
- 可以放心体验强推、reset、rebase 这些"危险动作"
- 履历上多一个持续维护的 GitHub 仓库，也是加分的

> 本系列示例仓库：[git-practice](https://github.com/yuxiangming/git-practice)，可以直接参考它的提交历史和分支结构。

## 二、第一步：在 GitHub 上创建仓库

1. 登录 [github.com](https://github.com)，右上角 **+** → **New repository**
2. 填写：
   - **Repository name**：`git-practice`
   - **Description**：Git 教程练习仓库（随便写）
   - **Public / Private**：公开可以当简历，私密练完删掉也行
   - ✅ 勾选 **Add a README file**（省得空仓库没有初始提交）
   - ✅ 选择 **Add .gitignore** → 挑一个模板（如 Node）
   - （可选）Add a license
3. 点 **Create repository**，复制仓库地址（HTTPS 即可）

## 三、第二步：SSH 免密推送（一次配置，终身省事）

HTTPS 每次推都要输密码/Token，配置 SSH 一劳永逸：

```bash
# 1. 生成密钥（一路回车即可）
ssh-keygen -t ed25519 -C "你的邮箱@example.com"

# 2. 查看公钥内容并复制
cat ~/.ssh/id_ed25519.pub

# 3. GitHub → Settings → SSH and GPG keys → New SSH key，粘贴公钥

# 4. 验证连接
ssh -T git@github.com     # 看到 "successfully authenticated" 即成功
```

然后克隆（注意用 SSH 地址）：

```bash
git clone git@github.com:你的用户名/git-practice.git
cd git-practice
```

## 四、第三步：初始化分支结构（对应第 04 章）

把 Git Flow 的骨架搭出来：

```bash
# develop 永久分支
git switch -c develop
git push -u origin develop

# GitHub 上把 develop 设为默认开发分支：
# Settings → Branches → default branch → develop（可选）
```

再到 GitHub 配置**保护分支**（重点体验）：

1. Settings → Branches → Add branch protection rule
2. Branch name pattern 填 `main`
3. 勾选 **Require a pull request before merging**（禁止直推，必须走 PR）
4. 保存。之后任何直推 main 都会被拒绝——试试 `git push origin main` 感受一下

## 五、第四步：完整实战流程（跟练清单）

下面这个演练把三章的功夫串成一条线，**建议一口气走完**：

### 场景 A：功能开发 → merge 合并（第 02、03 章）

```bash
# 1. 开功能分支
git switch develop
git switch -c feature/readme-tips

# 2. 开发：往 README 加一条小技巧，提交
echo "## 小技巧：git status 是最好的朋友" >> README.md
git add README.md
git commit -m "feat: README 增加使用小技巧"

# 3. 同时切回 develop，制造一条主线提交（模拟别人也在干活）
git switch develop
echo "## 更新日志" > CHANGELOG.md
git add CHANGELOG.md
git commit -m "docs: 添加更新日志"

# 4. 功能分支 rebase 到最新 develop（私有分支用 rebase）
git switch feature/readme-tips
git rebase develop

# 5. 用 merge 合回 develop，观察 --graph 的形状
git switch develop
git merge feature/readme-tips -m "merge: 合入 readme 技巧"
git branch -d feature/readme-tips
git log --oneline --graph --all
git push origin develop
```

### 场景 B：模拟发布 → 测试分支 → 打 Tag（第 04 章）

```bash
git switch -c release/v0.1.0
echo "版本 v0.1.0" >> CHANGELOG.md
git add CHANGELOG.md
git commit -m "chore: 发布准备 v0.1.0"
git push -u origin release/v0.1.0    # 体验：CI 会把 release 部署到"测试环境"

# 验收通过，合入 main 并打 Tag
git switch main
git pull
git merge release/v0.1.0 -m "release: v0.1.0"
git tag v0.1.0
git push origin main --tags

# 别忘了同步回 develop
git switch develop && git merge release/v0.1.0 && git push origin develop
```

### 场景 C：发起你的第一个 Pull Request（GitHub Flow 精髓）

```bash
git switch -c feature/pr-demo
echo "- [x] 第一个 PR" >> TODO.md
git add TODO.md && git commit -m "docs: TODO 记录 PR 练习"
git push -u origin feature/pr-demo
```

然后在 GitHub 网页上：

1. 仓库首页出现黄色提示条 **Compare & pull request**，点它
2. 写标题和说明，点 **Create pull request**
3. 打开 **Files changed**，体验逐行评论（review 的日常）
4. 点 **Merge pull request** → **Confirm merge**，注意选一下合并方式（见下方）
5. 删除远程分支，本地也删：`git switch main && git pull && git branch -d feature/pr-demo`

**PR 页面的三种合并方式**（就是第 03 章的两条路 + 折中）：

| 按钮 | 等价操作 | 效果 |
|---|---|---|
| Create a merge commit | `git merge` | 保留分支历史 + 合并提交 |
| Squash and merge | 把分支所有提交压成一个再合 | 历史干净，一条 PR 一条记录 |
| Rebase and merge | `git rebase` | 直线历史，无合并提交 |

### 场景 D：紧急修复演练 → hotfix（第 04 章）

```bash
git switch main && git switch -c hotfix/typo
# 修复一个"线上问题"（比如 README 里的错别字），提交
git switch main && git merge hotfix/typo
git tag v0.1.1 && git push origin main --tags
git switch develop && git merge hotfix/typo && git push origin develop
git branch -d hotfix/typo
```

## 六、危险动作体验区（练坏了就重建仓库）

在练习仓库里可以放心体验真实项目不敢碰的操作：

```bash
# 1. 回到过去：reset --hard + reflog 捡回来
git reset --hard HEAD~2           # 回退两个提交
git reflog                        # 找到之前的哈希
git reset --hard 之前的哈希        # 时光倒流回去了

# 2. 交互式变基：改写、合并、删除历史提交（仅限未推送/私有分支）
git rebase -i HEAD~3              # 打开编辑器，按提示 pick/squash/drop

# 3. 强推的边界：--force 与 --force-with-lease 的区别
git push --force-with-lease       # 远程有别人的新提交时会拒绝（安全）
```

> 体验完强烈建议：`Settings` → 页面最底部 **Delete this repository**，重建一个再练。删仓库本身就是练习的一部分。

## 七、进阶练习（自选）

- [ ] 给仓库写像样的 README：项目说明、徽章、目录
- [ ] 体验 GitHub Pages：Settings → Pages，把 README 做成一个网页
- [ ] 提交一个 Issue 给自己的仓库，然后从 Issue 里 "Create a branch"
- [ ] 给别人（或本站仓库）发一个真正的 PR
- [ ] 把练习仓库的提交做成"每日打卡"，坚持 30 天

## 八、本章小结

- 建仓库三件套：README、.gitignore、（可选）license
- SSH 免密：`ssh-keygen` → 加公钥 → `ssh -T git@github.com` 验证
- 保护分支让 main 只能走 PR，这是团队协作的第一道闸门
- PR 的三种合并方式对应第 03 章的 merge / squash / rebase
- 练习仓库可以随便玩危险命令，玩坏就删掉重建

## 九、毕业清单

完成以下全部，说明你已经达到"可以参与真实团队协作"的水平：

- [ ] 仓库建好，SSH 推送通畅
- [ ] main 设了保护分支，直推被拒绝过
- [ ] 场景 A/B/C/D 四个演练全部走通
- [ ] `git log --oneline --graph --all` 里能看到 feature、release、hotfix 的完整足迹
- [ ] 至少体验过一次 reset --hard + reflog 的时光倒流
- [ ] 删掉仓库重建过至少一次，并且不慌

恭喜毕业。下一步可以把这套规范带到真实项目中，或继续阅读本站的 [Jenkins CI/CD 系列](/series/jenkins-pipeline)——它正是建立在本章 Git 规范之上的。
