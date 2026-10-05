# mdtoc

给 Markdown 文件生成目录（Table of Contents）的小工具：解析标题，生成
GitHub 风格的锚点目录，在 `<!-- toc -->` 标记之间写入 / 更新 / 校验。

纯 Python 标准库，离线可用，无依赖。

## 安装

```bash
git clone https://github.com/ljiang9/mdtoc.git
cd mdtoc
python3 -m mdtoc --help
```

## 快速开始

```bash
# 打印目录
python3 -m mdtoc README.md

# 把目录写入 <!-- toc --> ... <!-- /toc --> 标记之间
python3 -m mdtoc --write README.md

# 文件里还没有标记？先插入（插在首个一级标题后面）
python3 -m mdtoc --insert README.md

# CI 校验：目录过期就报错退出（exit 1）
python3 -m mdtoc --check README.md

# 只收录到二级标题
python3 -m mdtoc --max-depth 2 README.md

# 批量校验一个目录下所有 .md
python3 -m mdtoc --check --dir ./docs
```

输出示例：

```markdown
- [示例文档](#示例文档)
  - [安装](#安装)
  - [安装](#安装-1)
    - [快速开始](#快速开始)
```

## 锚点规则（GitHub 风格，近似实现）

- 小写；空格/下划线转连字符；去掉标点符号
- 中文标题原样保留（如 `#安装` → `#安装`）
- 重复标题自动加后缀：`#安装`、`#安装-1`、`#安装-2`
- 代码块（``` / ~~~）里的 `#` 行会被跳过，不进目录

## 诚实说明

- slug 规则是**对 GitHub 锚点算法的近似**：常见标题完全一致，
  极生僻的标点组合可能与 GitHub 渲染有细微出入
- `--write` 要求文件里已有 `<!-- toc -->` / `<!-- /toc -->` 标记，
  没有标记会明确报错（不会悄悄乱插）；用 `--insert` 显式插入
- 目录只反映标题文本；标题改了但忘记 `--write` 时，`--check` 会报"已过期"

## License

MIT，见 [LICENSE](LICENSE)。
