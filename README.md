# Relicário — gerenciador de imagens

Aplicativo desktop (Python + PyQt6 + Pillow) para organizar e editar as imagens de uma pasta,
com visual de bosque bioluminescente: verdes profundos, musgo e luz difusa, com vermelho vivo reservado a alertas.
## Funcionalidades

- **Escolher pasta**: carrega JPG, JPEG, PNG, WEBP e BMP em uma grade de miniaturas com rolagem.
- **Detalhes**: clique numa miniatura para ver a prévia maior, dimensões, tamanho e formato.
- **Espelhar** horizontal/vertical, com prévia imediata (os botões alternam; clicar de novo desfaz).
- **Converter** para JPEG, JPG ou PNG. PNG com transparência → JPEG ganha fundo **branco**
  (a prévia já mostra o resultado).
- **Renomear** no campo de nome com validação ao digitar: bloqueia vazio, caracteres inválidos (`< > : " / \ | ? *`),
  nomes reservados do Windows, extensão digitada e nomes duplicados na pasta.
- **Salvar**: "Aplicar alterações" renomeia e aplica edições/conversões imediatamente, sem confirmação extra.
  Se só renomear, os bytes originais são preservados. Ao converter,
  o arquivo antigo é removido e o novo é gravado com a nova extensão
  (se já existir outro arquivo com esse nome, a operação é bloqueada).
  A gravação é segura: escreve num arquivo temporário e só então troca pelo original.
- **Atualização automática** da grade após cada alteração. `F5` recarrega a pasta.
- **Fundo atmosférico animado** com esporos luminosos, véus de luz e silhuetas sutis de musgo.

## Instalação

Requer Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Execução

```bash
python main.py
```

## Fonte dos títulos

A fonte **Cinzel** (licença OFL, incluída em `assets/fonts/`) é carregada automaticamente.
Se removida, o app usa Palatino/Book Antiqua/Georgia como alternativa serifada.

## Estrutura

```
main.py            ponto de entrada (carrega fontes e tema)
app/styles.py      paleta de cores e folha de estilos (QSS)
app/image_ops.py   lógica de imagem com Pillow (sem Qt): listagem, miniaturas, edição, validação
app/ui.py          interface: janela, grade de miniaturas, painel de detalhes, botões animados
assets/fonts/      fonte Cinzel (OFL)
```

## Notas técnicas

- **Miniaturas eficientes**: geradas em 4 threads, só para itens visíveis (+ margem) conforme a rolagem;
  JPEGs usam decodificação reduzida (`draft`); miniaturas de arquivos inalterados são reaproveitadas
  entre atualizações e as distantes da tela são descartadas em pastas muito grandes.
- **Tratamento de erros**: pasta sem permissão/inexistente, pasta sem imagens, arquivo corrompido,
  arquivo movido/apagado, sem permissão de escrita e nomes em conflito exibem mensagens amigáveis.
- **Metadados**: a orientação EXIF é aplicada à imagem e o perfil de cor ICC é preservado; demais
  metadados EXIF não são mantidos ao salvar. WEBP animado vira imagem estática.

## Como gerar um executável com ícone

Coloque o arquivo de ícone na pasta principal do projeto:

```text
relicario/
├── main.py
└── icone.ico
```

Substitua `main.py` pelo nome do arquivo principal do seu aplicativo.

### Como obter um arquivo `.ico`

Se você possui uma imagem PNG ou JPG, converta-a para `.ico` utilizando uma ferramenta como o [ConvertICO](https://convertico.com/).

Recomendações:
- Utilize uma imagem quadrada.
- Prefira resolução de 256 × 256 pixels.
- Utilize fundo transparente, se possível.

### ⚙️ 2. Instale o PyInstaller

Abra o terminal na pasta do projeto e execute:

```bash
python -m pip install pyinstaller
```

O PyInstaller será responsável por empacotar o aplicativo Python em um executável do Windows.

### 🚀 3. Gere o executável com o ícone

Execute o seguinte comando no terminal:

```bash
python -m PyInstaller --onefile --windowed --icon=icone.ico main.py
```

### O que cada opção faz?

| Opção | Descrição |
|---|---|
| `--onefile` | Gera um único arquivo executável. |
| `--windowed` | Evita abrir uma janela de terminal junto com o aplicativo. |
| `--icon=icone.ico` | Define o ícone personalizado do executável. |
| `main.py` | Indica o arquivo principal do programa. |

**Importante:** se o aplicativo precisa de um terminal para receber comandos ou exibir mensagens, remova a opção `--windowed`.

### 📦 4. Localize o executável

Após a compilação, o PyInstaller criará uma estrutura semelhante a esta:

```text
MeuAplicativo/
├── main.py
├── icone.ico
├── build/
├── dist/
│   └── main.exe
└── main.spec
```

O executável final estará na pasta `dist`.

Abra essa pasta e execute `main.exe`. O ícone personalizado deverá aparecer no Explorador de Arquivos.

### 🔄 5. Como trocar o ícone posteriormente

Se quiser mudar o ícone:

1. Substitua o arquivo `icone.ico` pela nova imagem.
2. Execute novamente o comando de compilação.
3. Abra o novo executável dentro da pasta `dist`.

Para gerar o programa novamente do zero, você pode executar:

```bash
python -m PyInstaller --clean --noconfirm --onefile --windowed --icon=icone.ico main.py
```

Esse comando limpa arquivos temporários de compilação e recria o executável.
