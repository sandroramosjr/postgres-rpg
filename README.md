# postgres-rpg

RPG de texto por turnos, desenvolvido em Python com persistência em PostgreSQL. O projeto demonstra modelos de domínio orientados a objetos e uma camada de repositórios baseada em SQL para personagens, equipamentos, inventário, habilidades, missões, histórico de batalhas e visualização de estatísticas.

## Funcionalidades

- Crie seus personagens, salve e carregue seu progresso
- Escolha entre 3 classes: Guerreiro, Mago, Ladino
- Batalhe por turnos contra inimigos
- Ganhe EXP e ouro para melhorar seus atributos e ganhar novas habilidades
- Complete missões repetíveis e colete recompensas em ouro e EXP
- Acesse o Histórico de suas batalhas e confira as suas estatísticas de combate
- Descanso na estalagem e recupere seu HP e MP por 50 ouro
- Compre e venda seus itens
- Venda automática de loot duplicado

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
