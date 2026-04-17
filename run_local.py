import os
os.environ["FLOW_PMO_DASH_MODULE"] = "dashboard_full"
os.environ["FLOW_PMO_DASH_ATTR"] = "app"
os.environ["FLOW_PMO_MODEL_URL"] = "https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/PowerBI_Model_latest.xlsx"
os.environ["FLOW_PMO_PORTFOLIO_CSV_URL"] = "https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/portfolio-bt-ns-latest-data.csv"
os.environ["FLOW_PMO_BOTTLENECK_CSV_URL_MAP"] = "https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/bottlenecks_consolidado_latest.xlsx"
os.environ["FLOW_PMO_FOUR_PS_KANBAN_CSV_URL"] = "https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/four_ps_kanban.csv"
os.environ["FLOW_PMO_DOWNSTREAM_CSV_URL_MAP"] = '{"W1NNER":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/w1nner-downstream-latest-data.csv","S1NC":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/s1nc-downstream-latest-data.csv","BEFINANCE":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/befinance-downstream-latest-data.csv","DATA&ANALYTICS":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/dataanalytics-downstream-latest-data.csv"}'
os.environ["FLOW_PMO_PROCESS_MINING_REPORT_URL"] = '{"w1nner":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/w1nner-process-mining-latest.xlsx","s1nc":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/s1nc-process-mining-latest.xlsx","befinance":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/befinance-process-mining-latest.xlsx","dataanalytics":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/dataanalytics-process-mining-latest.xlsx"}'
os.environ["FLOW_PMO_BITBUCKET_CSV_URL_MAP"] = '{"w1nner_commits":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/w1nner_commits.csv","w1nner_pullrequests":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/w1nner_pullrequests.csv","s1nc_commits":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/s1nc_commits.csv","s1nc_pullrequests":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/s1nc_pullrequests.csv","befinance_commits":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/befinance_commits.csv","befinance_pullrequests":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/befinance_pullrequests.csv","dataanalytics_commits":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/dataanalytics_commits.csv","dataanalytics_pullrequests":"https://w1-flow-pmo-dashboards.s3.us-east-1.amazonaws.com/dataanalytics_pullrequests.csv"}'
os.environ["FLOW_PMO_REMOTE_CACHE_TTL_SECONDS"] = "300"
os.environ["FLOW_PMO_ONE_PAGE_SLA_DAYS"] = "5"
os.environ["FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP"] = '{"W1NNER":5,"S1NC":5,"BEFINANCE":5,"DATA&ANALYTICS":5}'
os.environ["FLOW_PMO_PM_COST_PER_HOUR_MAP"] = '{"BF":212,"DT":182,"S1NC":167,"W1NNER":174}'
os.environ["FLOW_PMO_PORTFOLIO_BU_SALARY_MAP"] = '{"BeFinance":14000,"Dados":12000,"Sistemas - S1NC":11000,"Sistemas - W1NNER":11500,"Arquitetura":18000,"Cross":13000,"Cyber":13000,"Governanca":16000,"Infra":11500}'
os.environ["FLOW_PMO_PORTFOLIO_COST_MODEL"] = '{"fl_mensal":50000000,"budget_ti_pct":0.10,"fator_encargos":2.0,"custo_ferramentas_infra_mensal":35000,"dias_uteis_mes":22,"horas_dia":8,"fator_produtividade":0.75,"salario_medio_bruto":12000}'
os.environ["FLOW_PMO_PORTFOLIO_ROLE_SALARY_MAP"] = '{"Dev":10000,"Tech Lead":18000}'
os.environ["FLOW_PMO_ALLOWED_DOMAIN"] = "w1.com.br"
import api.index
print("Successfully loaded api.index")
