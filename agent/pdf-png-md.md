- run bash for `pdf -> png`

```bash
pixi run -e default python scripts/pdf_to_png.py agent/demo.pdf -o png/demo
```

- for codex prompt, `png -> md`

```
将 @png/demo 目录下的 png 文件 转换成 markdown 文件, 输出同名 md 文件到 `md/demo/`, 逐个处理每一个文件, 要求:

- 将 image 文件加入到 context 中, 直接理解这个 image 而不是通过额外的转换的方式
- 不要使用任何的 ocr 方案
- 不需要额外的本地图片处理操作
- 输出保持最大的接近原始文件, 不需要输出额外的信息
- 不要过分思考, 抓住核心的目标是内容转换
```
