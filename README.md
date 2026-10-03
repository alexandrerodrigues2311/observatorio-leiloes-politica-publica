# Observatório dos Leilões Minerais — Política Pública

Projeto independente do artigo e do painel submetidos anteriormente. Cadastro de 02/10/2026; CFEM até 06/2026.

## Conteúdo

- `site/`: painel estático com consulta dos 7.528 ciclos e 30.861 chaves da união dos recortes de estoque.
- `src/`: reconstrução de vínculos, modelos logísticos e de duração, estoque nacional e cinco revisões.
- `notebooks/`: caderno autocontido para Google Colab com scripts e base analítica mínima sem identificadores fiscais pessoais.
- `results/`: agregados, dicionários e hashes dos insumos.

## Reprodução

Abra o notebook e siga as células. Os insumos oficiais podem mudar. A reprodução exata exige os arquivos com os hashes do manifesto; o caderno interrompe por padrão se houver diferença. Use Python 3 e NumPy. O processamento nacional percorre milhões de eventos. As rotinas foram executadas localmente; o caderno foi montado com os mesmos scripts e teve sua sintaxe verificada.

## Resultados e limites

Foram identificados 896 ciclos com cessão estrita, 1.111 ocorrências e 845 ciclos com transição candidata de titular. O recorte estratégico histórico contém 3.313 ciclos. O estoque ativo nas fases 8 e 15 contém 22.749 processos e a aptidão SOPLE contém 18.296, com 10.184 na interseção.

Cessão não prova especulação. A lista de 2021 não certifica enquadramento pela PNMCE. Fase e aptidão não certificam ofertabilidade. Complemento do sinal de não pagamento não é receita confirmada. Os 144 cenários de incentivos usam parâmetros hipotéticos e não estimam preço ótimo causal.

Dados pessoais de titulares e observações livres de eventos não são publicados neste repositório. O relatório interno é entregue separadamente ao autor. Este produto analítico não constitui manifestação institucional da ANM.

## Acesso

[Google Colab](https://colab.research.google.com/drive/1RjjzU5tZpxo1UASG1LxkruDqcuR59-M_)

Fontes oficiais: [Cadastro Mineiro](https://dadosabertos.anm.gov.br/SCM/) e [SOPLE](https://dadosabertos.anm.gov.br/SOPLE/).
