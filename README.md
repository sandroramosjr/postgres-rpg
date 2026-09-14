# postgres-rpg

RPG de texto por turnos, desenvolvido em Python com persistência em PostgreSQL. O projeto demonstra modelos de domínio orientados a objetos e uma camada de repositórios baseada em SQL para personagens, equipamentos, inventário, habilidades, missões, histórico de batalhas e visões estatísticas.

## Funcionalidades

- Criar e carregar personagens nomeados (Guerreiro, Mago, Ladino)
- Atributos, espaços de equipamento, inventário e habilidades de classe
- Batalhas por turnos contra inimigos do catálogo
- EXP e ouro por vitórias, além de ouro extra e crescimento de atributos ao subir de nível
- Missões repetíveis, com progresso, EXP e ouro de conclusão salvos no banco de dados
- Missões bloqueadas por nível exibidas no menu
- Histórico das últimas 20 batalhas para cada vitória, derrota ou fuga
- Descanso na estalagem por 50 ouro
- Compra e venda de itens; itens não equipados são vendidos por metade do preço
- Venda automática de loot duplicado, com registro e estatísticas de vendas
- Habilidades do Mago balanceadas para causar dano relevante com custo de MP reduzido
- Pausas entre cenas para facilitar a leitura durante o jogo
- Estatísticas no jogo obtidas das visões SQL e do histórico de vendas

## Estrutura

```
src/rpg/models/        Domínio orientado a objetos (LivingEntity, Character, Enemy, Inventory, ...)
src/rpg/repositories/  SQL direto via psycopg, incluindo vendas e estatísticas
src/rpg/combat.py      Resolução dos turnos
src/rpg/cli.py         Interface de texto
sql/schema.sql         Tabelas, índices e visões
sql/seed.sql           Classes, equipamentos, inimigos e missões
sql/stats.sql          Exemplos de consultas analíticas
```

## Configuração

1. Inicie o PostgreSQL (Docker):

   ```bash
   docker compose up -d
   ```

2. Configure o ambiente Python:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```

   No VS Code, abra a pasta do projeto e selecione `.venv\Scripts\python.exe` quando
   solicitado. A configuração do workspace define `src` como caminho de importação e
   habilita automaticamente a descoberta de testes do pytest.

3. Jogue:

   ```bash
   python -m rpg
   ```

   Execute esse comando na raiz do projeto com `PYTHONPATH=src`, ou:

   ```bash
   python -m pip install -e .
   python -m rpg
   ```

   Se você não fizer a instalação editável, use:

   ```bash
   set PYTHONPATH=src
   python -m rpg
   ```

   No VS Code, você também pode usar a configuração de execução `Run RPG` ou executar
   as tarefas `PostgreSQL: start` e `Tests: pytest` na Paleta de Comandos.

A primeira conexão aplica `sql/schema.sql` e `sql/seed.sql` se a tabela `characters` não existir.

### Saves de debug

Com o PostgreSQL iniciado, crie os três saves prontos para testes com:

```powershell
Get-Content .\sql\debug_saves.sql | docker compose exec -T db psql -U rpg -d rpg
```

O script cria `WAR`, `ROG` e `MAG` no nível 10, com 9999 ouro, todos os equipamentos
no inventário, um conjunto equipado e todas as habilidades disponíveis da classe.

## Executável Windows

Para gerar a versão 1.0 em um único executável, com o ambiente virtual criado:

```powershell
.\build_exe.ps1
```

O arquivo será criado em `dist\postgres-rpg.exe`. O executável inclui o jogo, suas
dependências e os scripts SQL, mas o PostgreSQL continua sendo externo e deve estar
disponível, normalmente com `docker compose up -d`.

## Testes

```bash
set PYTHONPATH=src
pytest
```

Os testes de domínio não precisam do PostgreSQL.

## URL do banco de dados

Padrão: `postgresql://rpg:rpg@localhost:5432/rpg` (consulte `.env.example`).
