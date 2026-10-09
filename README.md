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
- Para gerar um executável: `pip install pyinstaller` e `pyinstaller --noconsole --onefile main.py`.
