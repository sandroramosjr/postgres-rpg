# Guia do projeto postgres-rpg

Este documento explica como o projeto está organizado e como suas partes trabalham juntas. A ideia é servir como um mapa de estudo: você pode acompanhar o caminho de uma ação do jogador desde o menu até o domínio Python, o banco PostgreSQL e a persistência final.

## 1. Visão geral

O projeto é um RPG de texto por turnos escrito em Python, com PostgreSQL como banco de dados. Ele combina três ideias principais:

- **Python e orientação a objetos:** regras de personagens, atributos, equipamentos, habilidades, missões e combate.
- **SQL e modelagem relacional:** tabelas para o catálogo do jogo e para o estado salvo de cada personagem.
- **Docker:** executa o PostgreSQL localmente sem exigir uma instalação manual do servidor no computador.

O programa não possui uma interface gráfica. A interface é o terminal: o jogador escolhe opções numeradas, combate, compra equipamentos, aceita missões, sobe de nível e salva o personagem.
Após resultados de batalha, descanso, compras, vendas e outras ações, o jogo aguarda
uma tecla antes de retornar ao menu para facilitar a leitura.

## 2. Estrutura do repositório

```text
postgres-rpg/
├── .vscode/             Configurações para trabalhar no VS Code
├── sql/                 Estrutura, dados iniciais e consultas analíticas
├── src/rpg/             Código Python da aplicação
├── tests/               Testes automatizados
├── .env                 Configuração local, como a URL do banco
├── .env.example         Exemplo da configuração de ambiente
├── docker-compose.yml   Definição do PostgreSQL em Docker
├── pyproject.toml       Metadados do pacote e comando da aplicação
├── requirements.txt     Dependências Python
├── pytest.ini           Configuração do pytest
└── README.md            Instruções rápidas do projeto
```

Arquivos iniciados com ponto, como `.env` e `.vscode`, são arquivos de configuração. A pasta `.venv`, criada localmente para o ambiente Python, também pode existir, mas não faz parte do código da aplicação.

## 3. Pasta `src/rpg`

Esta é a aplicação Python. O pacote está dentro de `src` para separar o código instalável dos arquivos de configuração e dos testes.

### `__main__.py`

É o ponto de entrada usado por:

```text
python -m rpg
```

Ele carrega as variáveis do arquivo `.env` e chama `main()` no módulo `cli.py`.

### `cli.py`

Contém a interface de terminal e os menus do jogo. Entre suas responsabilidades estão:

- menu inicial para criar, carregar, excluir personagem ou sair;
- menu da cidade;
- seleção de classes, inimigos, missões, habilidades, itens e equipamentos;
- exibição da ficha do personagem;
- loja, inventário, histórico, estatísticas e descanso;
- condução da batalha turno a turno.

O CLI não deveria conter as regras profundas do domínio. Ele recebe a entrada do jogador, chama os serviços apropriados e apresenta as mensagens em português.

### `game.py`

Contém `GameService`, a camada de aplicação que coordena uma ação completa do jogo. Ele
recebe os repositórios e o motor de combate por injeção de dependência. A função
`create_game_service()` faz a composição das implementações no ponto de entrada, deixando
o serviço modular e testável.

Exemplos de responsabilidades:

- salvar personagens;
- comprar equipamentos, verificando nível e ouro;
- descansar na estalagem;
- cobrar 50 de ouro pelo descanso na estalagem;
- vender itens do inventário por metade do preço de compra;
- vender automaticamente um equipamento recebido como loot quando já houver uma cópia no inventário;
- resolver uma batalha concluída;
- conceder EXP, ouro, níveis, loot e recompensas de missão;
- registrar o resultado da batalha no banco.

Essa camada é importante porque evita que o CLI precise conhecer todos os detalhes de SQL e persistência.

### `combat.py`

Implementa o motor de combate:

- cálculo de dano com variação aleatória;
- ataques básicos;
- habilidades que consomem MP;
- ataques dos inimigos;
- definição de quem age primeiro com base na velocidade.

`BattleLog` é o objeto que acumula o resultado de uma batalha: vitória, derrota ou fuga, número de turnos e dano causado/recebido.

## 4. Pasta `src/rpg/models`

Esta pasta contém os objetos do domínio. Eles representam as coisas que existem dentro do jogo, independentemente de como são salvas no PostgreSQL.

### `entity.py`

Define `LivingEntity`, a abstração comum de seres que podem participar de combate. Ela concentra comportamentos como:

- saber se está vivo;
- receber dano;
- recuperar HP e MP.

`Character` e `Enemy` são especializações dessa entidade.

### `character.py`

Define o personagem do jogador e `CharacterClass`. Um personagem possui:

- nome, classe, nível, EXP e ouro;
- atributos de HP, MP, ataque, defesa e velocidade;
- inventário e equipamentos equipados;
- habilidades aprendidas;
- missões aceitas e seu progresso.

Também contém as regras de evolução: ganho de EXP, subida de nível, aumento de atributos, ouro de nível, aprendizado de habilidades e registro de eliminações para missões.

### `enemy.py`

Define os inimigos catalogados no banco. O método `clone()` cria uma cópia nova para cada combate, evitando que o HP perdido em uma luta altere o inimigo usado como modelo no catálogo.

Os nomes atuais dos inimigos incluem `Slime`, `Lobo da Floresta`, `Bandido`, `Morcego da Caverna` e `Ogro`.

### `stats.py`

Define o objeto `Stats`, que guarda HP, MP, ataque, defesa e velocidade. Também aplica bônus de equipamentos e limita os valores de HP/MP aos seus máximos válidos.

### `equipment.py`

Define `Equipment` e `Inventory`.

- `Equipment` representa uma arma, armadura ou acessório.
- `Inventory` controla itens e quantidades.
- O personagem pode equipar um item por espaço.
- Itens não equipados podem ser vendidos por metade do preço de compra, uma unidade por vez.
- Os bônus equipados alteram seus atributos efetivos.

### `skill.py`

Define habilidades de combate, incluindo nome, descrição, percentual de dano, custo de MP, nível mínimo e classe compatível.

### `quest.py`

Define `Quest` e `QuestProgress`. A missão descreve o inimigo-alvo, quantidade necessária de eliminações, nível mínimo e recompensas. O progresso acompanha a quantidade de eliminações e muda de `active` para `completed` ao ser concluído.

### `battle.py`

Define `BattleRecord`, o objeto usado para representar uma linha do histórico de batalhas carregada do banco.

### `__init__.py`

Reexporta os principais modelos para facilitar imports em outras partes do pacote.

## 5. Pasta `src/rpg/repositories`

Os repositórios são a camada responsável por conversar com o PostgreSQL. Eles usam `psycopg` e SQL explícito, em vez de esconder as consultas atrás de um ORM.

Essa separação permite que os modelos continuem focados em regras de jogo, enquanto os repositórios cuidam de transformar linhas do banco em objetos Python e vice-versa.

### `catalog_repository.py`

Lê o catálogo que é compartilhado por todos os personagens:

- classes;
- equipamentos;
- inimigos;
- habilidades.

### `character_repository.py`

Cuida da vida completa de um personagem salvo:

- criação;
- carregamento por nome;
- atualização de atributos;
- inventário;
- equipamentos equipados;
- habilidades;
- missões;
- exclusão do save.

A exclusão funciona porque as tabelas relacionadas usam `ON DELETE CASCADE`, removendo os dados dependentes do personagem junto com ele.

### `quest_repository.py`

Busca as missões disponíveis para o nível do personagem, remove apenas as missões
atualmente ativas e também informa as missões bloqueadas por nível. Missões concluídas
podem ser aceitas novamente.

### `battle_repository.py`

Registra batalhas e carrega as últimas 20 batalhas de um personagem.

### `stats_repository.py`

Executa consultas de leitura para a tela de estatísticas:

- resumo do personagem;
- ranking de personagens;
- desempenho contra inimigos;
- progresso das missões;
- valor do inventário.
- quantidade e valor das vendas, incluindo vendas automáticas de loot duplicado.

A taxa de vitória contra inimigos é calculada considerando vitórias e derrotas. Fugas não entram nessa porcentagem.

### `__init__.py`

Reexporta os repositórios principais.

## 6. Pasta `sql`

A pasta SQL define o modelo persistente e os dados do jogo.

### `schema.sql`

Cria as tabelas, restrições, índices e views.

As principais tabelas são:

- `character_classes`: classes jogáveis;
- `characters`: estado principal dos personagens;
- `equipment`: catálogo de itens;
- `inventory`: itens de cada personagem;
- `equipped_items`: equipamentos atualmente usados;
- `item_sales`: histórico de vendas manuais e automáticas;
- `skills`: habilidades disponíveis;
- `character_skills`: habilidades aprendidas;
- `enemies`: catálogo de inimigos e recompensas;
- `quests`: catálogo de missões;
- `character_quests`: progresso das missões por personagem;
- `battles`: histórico de combates.

As chaves estrangeiras conectam essas tabelas. Por exemplo, um personagem pode ter muitas linhas em `inventory`, e essas linhas são removidas automaticamente quando o personagem é excluído.

As views são consultas salvas para relatórios, como estatísticas de batalhas, ameaça/desempenho dos inimigos e conclusão de missões.

As estatísticas do personagem também mostram a quantidade de itens vendidos, o ouro
obtido com vendas e o detalhamento por equipamento.

### `seed.sql`

Insere os dados iniciais do jogo: classes, equipamentos, habilidades, inimigos e missões. É o catálogo que permite iniciar uma partida sem cadastrar manualmente cada item.

Se o banco já possui dados, editar o seed não altera automaticamente os registros existentes. Nesse caso, é necessário executar um `UPDATE` ou recriar o volume do PostgreSQL.

### `stats.sql`

Contém consultas analíticas de exemplo para consultar as views diretamente no PostgreSQL. O jogo usa consultas semelhantes por meio de `StatsRepository`.

### `debug_saves.sql`

Cria os saves `WAR`, `ROG` e `MAG` para testes de balanceamento e usabilidade. Todos
ficam no nível 10, recebem 9999 ouro, todos os equipamentos no inventário, um conjunto
equipado e todas as habilidades disponíveis da classe. O script pode ser reaplicado,
pois substitui saves existentes com esses nomes:

```powershell
Get-Content .\sql\debug_saves.sql | docker compose exec -T db psql -U rpg -d rpg
```

## 7. Docker e PostgreSQL

O arquivo `docker-compose.yml` define um serviço chamado `db` usando a imagem `postgres:16-alpine`.

A configuração cria:

- usuário `rpg`;
- senha `rpg`;
- banco `rpg`;
- porta local `5432`;
- volume persistente `rpg_pgdata`.

Para iniciar o banco:

```text
docker compose up -d
```

Para conferir o serviço:

```text
docker compose ps
```

Para parar os containers:

```text
docker compose down
```

O volume mantém os dados entre reinicializações. Os arquivos `schema.sql` e `seed.sql` são montados no diretório especial de inicialização do PostgreSQL. O PostgreSQL normalmente executa esses scripts apenas quando o volume é criado pela primeira vez.

Além disso, a aplicação possui uma proteção em `db.py`: ao conectar, ela verifica se a tabela `characters` existe. Se não existir, aplica o schema e o seed usando a própria aplicação.

## 8. Configuração e dependências

### `.env` e `.env.example`

A variável principal é `DATABASE_URL`, que informa ao `psycopg` como conectar ao banco. O `.env.example` serve como modelo; o `.env` é a cópia local usada pelo desenvolvedor.

### `requirements.txt`

Lista as dependências usadas para executar e testar o projeto:

- `psycopg[binary]`: conexão com PostgreSQL;
- `python-dotenv`: leitura do `.env`;
- `pytest`: testes automatizados.

### `pyproject.toml`

Descreve o pacote Python, sua versão, requisito mínimo de Python e o comando instalado como `postgres-rpg`. Também configura a descoberta dos pacotes dentro de `src`.

### `pytest.ini`

Configura o pytest para encontrar o código em `src` e os testes na pasta `tests`.

## 9. Pasta `tests`

`tests/test_domain.py` testa as regras de domínio sem precisar de PostgreSQL. Isso torna os testes rápidos e isolados.

Os testes cobrem, entre outros pontos:

- bônus de equipamentos;
- evolução por EXP;
- conclusão de missões;
- dano mínimo de combate;
- consumo de MP por habilidades;
- iniciativa baseada em velocidade;
- HP adicional fornecido por equipamentos.

Testes de integração com PostgreSQL ainda seriam uma evolução natural: eles poderiam testar criação, carregamento, compra, histórico, exclusão de saves e as views estatísticas em um banco descartável.

Para executar os testes:

```text
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m pytest -q
```

## 10. Pasta `.vscode`

Essa pasta integra o projeto ao VS Code:

- `settings.json`: seleciona o ambiente `.venv`, adiciona `src` ao caminho de análise, configura pytest e carrega `.env`;
- `launch.json`: oferece a configuração `Run RPG` para executar `python -m rpg` no depurador;
- `tasks.json`: oferece tarefas para iniciar/parar/verificar o PostgreSQL e executar os testes;
- `extensions.json`: recomenda as extensões Python, Debugpy e Docker.

## 11. Fluxo de execução

O fluxo normal de inicialização é:

```text
python -m rpg
    ↓
__main__.py carrega .env
    ↓
cli.main() abre uma conexão
    ↓
db.initialize_schema() verifica o banco
    ↓
create_game_service() compõe repositórios e motor de combate
    ↓
GameService coordena a operação
    ↓
cli.py mostra o menu ao jogador
```

Quando o jogador realiza uma ação, o caminho costuma ser:

```text
Entrada do jogador
    ↓
CLI interpreta a opção
    ↓
GameService coordena a operação
    ↓
Modelo aplica as regras de domínio
    ↓
Repository consulta ou atualiza o PostgreSQL
    ↓
Transação é confirmada com commit
    ↓
CLI mostra o resultado
```

## 12. Exemplo: uma vitória em combate

1. O CLI carrega os inimigos pelo `CatalogRepository`.
2. O jogador escolhe um inimigo pela posição exibida no menu.
3. O CLI clona o inimigo para criar uma instância nova de combate.
4. `CombatEngine` calcula os ataques, dano e consumo de MP.
5. Ao vencer, `GameService.resolve_battle()` concede EXP, ouro e possível loot.
6. O personagem atualiza o progresso das missões.
7. `BattleRepository` grava o resultado em `battles`.
8. `CharacterRepository` salva atributos, inventário, equipamentos, habilidades e missões.
9. A transação é confirmada no PostgreSQL.

## 13. Exemplo: exclusão de um save

1. O jogador escolhe `Excluir personagem` no menu inicial.
2. O CLI mostra os personagens em ordem e pede uma confirmação explícita digitando `DELETAR`.
3. `CharacterRepository.delete_by_name()` executa `DELETE FROM characters`.
4. As chaves estrangeiras com `ON DELETE CASCADE` removem inventário, equipamentos, habilidades, missões e batalhas relacionadas.
5. A transação é confirmada.

Esse fluxo mantém a interface simples, mas usa a integridade referencial do banco para evitar dados órfãos.

## 14. Executável único

O jogo versão 1.0 pode ser distribuído como um executável Windows usando PyInstaller. O arquivo
embute o código Python, as dependências e os scripts SQL. O PostgreSQL continua sendo
um serviço externo e precisa estar disponível, normalmente pelo Docker Compose.

Com o ambiente virtual criado, execute na raiz do projeto:

```powershell
.\build_exe.ps1
```

O resultado será `dist\postgres-rpg.exe`. Para executar em outra máquina, copie também
o arquivo `.env` configurado e garanta que o PostgreSQL esteja acessível pela URL definida
em `DATABASE_URL`. O `.exe` não inclui o servidor PostgreSQL nem os dados persistidos.

## 15. Como estudar o projeto

Uma ordem prática para aprender o código é:

1. Ler este guia e o `README.md`.
2. Ler `models/stats.py`, `models/entity.py` e `models/character.py`.
3. Ler `combat.py` para entender a resolução de turnos.
4. Ler `game.py` para ver como uma ação completa é coordenada.
5. Ler `cli.py` para conectar os menus às funcionalidades.
6. Ler `schema.sql` para relacionar os objetos Python às tabelas.
7. Ler `character_repository.py` e os demais repositórios para entender a persistência.
8. Executar os testes e modificar uma regra pequena, observando como o comportamento muda.

A regra geral é: **modelos decidem regras do jogo, serviços coordenam casos de uso, repositórios persistem dados, SQL define a estrutura do banco e o CLI conversa com o jogador**.
