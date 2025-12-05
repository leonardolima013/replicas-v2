import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Activity, AlertTriangle, TrendingUp, Database } from "lucide-react";
import {
  getStatistics,
  getPreview,
  type StatisticsResponse,
  type ColumnStatistics,
} from "../../../services/validationService";
import WeightConsistencyChart from "../components/WeightConsistencyChart";

interface KPICardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  status?: "success" | "warning" | "error";
  subtitle?: string;
}

const KPICard = ({
  title,
  value,
  icon,
  status = "success",
  subtitle,
}: KPICardProps) => {
  const statusColors = {
    success: "text-emerald-500",
    warning: "text-amber-500",
    error: "text-rose-500",
  };

  return (
    <div className="bg-zinc-900 rounded-lg p-6 border border-zinc-800">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-zinc-500 text-sm font-medium">{title}</p>
          <p className={`text-3xl font-bold mt-2 ${statusColors[status]}`}>
            {value}
          </p>
          {subtitle && <p className="text-zinc-600 text-xs mt-1">{subtitle}</p>}
        </div>
        <div className={`${statusColors[status]}`}>{icon}</div>
      </div>
    </div>
  );
};

export default function StatisticsStep() {
  const { projectId } = useParams<{ projectId: string }>();
  const [statistics, setStatistics] = useState<StatisticsResponse | null>(null);
  const [scatterData, setScatterData] = useState<any[]>([]);
  const [nullCounts, setNullCounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (projectId) {
      loadStatistics();
      loadScatterData();
      loadNullCounts();
    }
  }, [projectId]);

  const loadStatistics = async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      const data = await getStatistics(projectId);
      setStatistics(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar estatísticas");
    } finally {
      setLoading(false);
    }
  };

  const loadScatterData = async () => {
    if (!projectId) return;

    try {
      // Carregar amostra dos dados para scatter plot (500 itens)
      const preview = await getPreview(projectId, 1, 500);
      const points = preview.rows
        .filter((row) => row.net_weight && row.gross_weight)
        .map((row, index) => ({
          net: parseFloat(row.net_weight) || 0,
          gross: parseFloat(row.gross_weight) || 0,
          id: row.id || row.search_ref || `Item ${index + 1}`,
          isError: parseFloat(row.net_weight) > parseFloat(row.gross_weight),
        }));
      setScatterData(points);
    } catch (err) {
      console.error("Erro ao carregar dados de scatter:", err);
    }
  };

  const loadNullCounts = async () => {
    if (!projectId) return;

    try {
      // Carregar preview completo e contar nulls manualmente
      const preview = await getPreview(projectId, 1, 1000);

      // Contar valores nulos/vazios por coluna
      const counts: Record<string, number> = {};
      preview.columns.forEach((col) => {
        counts[col] = 0;
      });

      preview.rows.forEach((row) => {
        preview.columns.forEach((col) => {
          const value = row[col];
          if (
            value === null ||
            value === undefined ||
            value === "" ||
            value === "nan" ||
            value === "null"
          ) {
            counts[col]++;
          }
        });
      });

      // Converter para array e ordenar por contagem (top 5)
      const nullData = Object.entries(counts)
        .map(([column, count]) => ({
          column,
          count,
          percentage: ((count / preview.total_rows) * 100).toFixed(1),
        }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);

      setNullCounts(nullData);
    } catch (err) {
      console.error("Erro ao contar nulos:", err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-900/20 border border-rose-500 rounded-lg p-4">
        <p className="text-rose-500">{error}</p>
      </div>
    );
  }

  if (!statistics) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <p className="text-zinc-500">Nenhuma estatística disponível</p>
      </div>
    );
  }

  // Calcular KPIs
  const totalViolations =
    statistics.violations.count_weight_error +
    statistics.violations.count_negative;

  // Calcular outliers extremos (valores 100x maiores que a mediana ou além de 3x desvio padrão)
  const calculateOutliers = (stats: ColumnStatistics[]) => {
    let outlierCount = 0;
    const extremeOutliers: string[] = [];

    stats.forEach((stat) => {
      if (
        stat.avg !== null &&
        stat.stddev !== null &&
        stat.max !== null &&
        stat.min !== null &&
        stat.q50 !== null
      ) {
        // Regra 1: Valores além de 3× desvio padrão
        const upperBound = stat.avg + 3 * stat.stddev;
        const lowerBound = stat.avg - 3 * stat.stddev;

        // Regra 2: Valores 100× maiores que a mediana (erro quase certo)
        const extremeUpperBound = stat.q50 * 100;

        if (stat.max > upperBound || stat.min < lowerBound) {
          outlierCount++;
        }

        // Detectar outliers extremos (erro de digitação provável)
        if (stat.q50 > 0 && stat.max > extremeUpperBound) {
          extremeOutliers.push(
            `${stat.column}: max=${stat.max.toFixed(
              2
            )} é 100× maior que mediana=${stat.q50.toFixed(2)}`
          );
        }
      }
    });

    return { count: outlierCount, extremeOutliers };
  };

  const outlierInfo = calculateOutliers(statistics.summary);
  const outliers = outlierInfo.count;

  // Calcular saúde dos dados (simplificado: 100% - % de violações)
  const healthPercentage =
    nullCounts.length > 0
      ? (100 - parseFloat(nullCounts[0].percentage)).toFixed(1)
      : "100";

  // Dados para boxplot simplificado (usando quartis)
  const dimensionStats = statistics.summary.filter((s) =>
    ["width", "height", "depth"].includes(s.column)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-zinc-100">
          Dashboard de Estatísticas
        </h2>
        <p className="text-zinc-500 mt-1">
          Análise avançada para identificar anomalias e outliers nos dados
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard
          title="Saúde dos Dados"
          value={`${healthPercentage}%`}
          icon={<Activity className="w-6 h-6" />}
          status={parseFloat(healthPercentage) > 95 ? "success" : "warning"}
          subtitle="Baseado em completude de dados"
        />
        <KPICard
          title="Violações Físicas"
          value={totalViolations}
          icon={<AlertTriangle className="w-6 h-6" />}
          status={totalViolations === 0 ? "success" : "error"}
          subtitle="Peso líquido > bruto ou negativos"
        />
        <KPICard
          title="Outliers Potenciais"
          value={outliers}
          icon={<TrendingUp className="w-6 h-6" />}
          status={outliers === 0 ? "success" : "warning"}
          subtitle="Valores além de 3× desvio padrão"
        />
      </div>

      {/* Seção de Pesos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Scatter Chart Inteligente */}
        <WeightConsistencyChart data={scatterData} />

        {/* Card de Aviso */}
        <div className="bg-zinc-900 rounded-lg p-6 border border-zinc-800 space-y-4">
          <h3 className="text-lg font-semibold text-zinc-100">
            Análise de Correlação
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-zinc-400">
                Correlação Peso Líquido/Bruto:
              </span>
              <span className="text-xl font-bold text-emerald-500">
                {statistics.correlation !== null
                  ? statistics.correlation.toFixed(3)
                  : "N/A"}
              </span>
            </div>

            {statistics.correlation !== null &&
              statistics.correlation < 0.8 && (
                <div className="bg-amber-900/20 border border-amber-500 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-amber-500 font-medium text-sm">
                        Correlação Baixa
                      </p>
                      <p className="text-zinc-400 text-xs mt-1">
                        Correlação abaixo de 0.8 pode indicar dados
                        inconsistentes entre peso líquido e bruto.
                      </p>
                    </div>
                  </div>
                </div>
              )}

            {statistics.violations.count_weight_error > 0 && (
              <div className="bg-rose-900/20 border border-rose-500 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-rose-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-rose-500 font-medium text-sm">
                      Violações Detectadas
                    </p>
                    <p className="text-zinc-400 text-xs mt-1">
                      {statistics.violations.count_weight_error} produto(s) com
                      peso líquido maior que bruto.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {statistics.violations.count_negative > 0 && (
              <div className="bg-rose-900/20 border border-rose-500 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-rose-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-rose-500 font-medium text-sm">
                      Valores Negativos
                    </p>
                    <p className="text-zinc-400 text-xs mt-1">
                      {statistics.violations.count_negative} valor(es)
                      negativo(s) detectado(s) em dimensões ou pesos.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {outlierInfo.extremeOutliers.length > 0 && (
              <div className="bg-rose-900/20 border border-rose-500 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-rose-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-rose-500 font-medium text-sm">
                      ⚠️ Outliers Extremos Detectados
                    </p>
                    <p className="text-zinc-400 text-xs mt-1">
                      Valores 100× maiores que a mediana (provável erro de
                      digitação):
                    </p>
                    <ul className="text-zinc-400 text-xs mt-2 space-y-1 ml-4 list-disc">
                      {outlierInfo.extremeOutliers
                        .slice(0, 3)
                        .map((outlier, idx) => (
                          <li
                            key={idx}
                            className="text-rose-400 font-mono text-[10px]"
                          >
                            {outlier}
                          </li>
                        ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {statistics.correlation !== null &&
              statistics.correlation >= 0.8 &&
              totalViolations === 0 &&
              outlierInfo.extremeOutliers.length === 0 && (
                <div className="bg-emerald-900/20 border border-emerald-500 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <Activity className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-emerald-500 font-medium text-sm">
                        Dados Consistentes
                      </p>
                      <p className="text-zinc-400 text-xs mt-1">
                        Correlação forte e sem violações físicas detectadas.
                      </p>
                    </div>
                  </div>
                </div>
              )}
          </div>
        </div>
      </div>

      {/* Seção de Distribuição (Boxplots Simplificados) */}
      {dimensionStats.length > 0 && (
        <div className="bg-zinc-900 rounded-lg p-6 border border-zinc-800">
          <h3 className="text-lg font-semibold text-zinc-100 mb-4">
            Análise de Dimensões e Outliers
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={dimensionStats}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
              <XAxis
                dataKey="column"
                stroke="#a1a1aa"
                tick={{ fill: "#a1a1aa" }}
              />
              <YAxis stroke="#a1a1aa" tick={{ fill: "#a1a1aa" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#18181b",
                  border: "1px solid #3f3f46",
                  borderRadius: "0.5rem",
                  color: "#fafafa",
                }}
                formatter={(value: any) => [
                  typeof value === "number" ? value.toFixed(2) : value,
                  "",
                ]}
              />
              <Bar dataKey="min" fill="#3b82f6" name="Mínimo" />
              <Bar dataKey="q25" fill="#10b981" name="Q25" />
              <Bar dataKey="q50" fill="#f59e0b" name="Mediana (Q50)" />
              <Bar dataKey="q75" fill="#8b5cf6" name="Q75" />
              <Bar dataKey="max" fill="#ef4444" name="Máximo" />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-zinc-500 text-sm mt-4">
            Distribuição dos quartis para detectar outliers. Valores muito
            distantes dos quartis podem indicar anomalias.
          </p>
        </div>
      )}

      {/* Seção de Completude */}
      {nullCounts.length > 0 && (
        <div className="bg-zinc-900 rounded-lg p-6 border border-zinc-800">
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-5 h-5 text-zinc-400" />
            <h3 className="text-lg font-semibold text-zinc-100">
              Completude dos Dados (Top 5 Colunas com Nulos)
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={nullCounts}
              layout="vertical"
              margin={{ top: 20, right: 30, left: 100, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
              <XAxis
                type="number"
                stroke="#a1a1aa"
                tick={{ fill: "#a1a1aa" }}
              />
              <YAxis
                type="category"
                dataKey="column"
                stroke="#a1a1aa"
                tick={{ fill: "#a1a1aa" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#18181b",
                  border: "1px solid #3f3f46",
                  borderRadius: "0.5rem",
                  color: "#fafafa",
                }}
                formatter={(value: any, _name: string, props: any) => [
                  `${value} (${props.payload.percentage}%)`,
                  "Valores Nulos",
                ]}
              />
              <Bar dataKey="count" name="Valores Nulos">
                {nullCounts.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      parseFloat(entry.percentage) > 10
                        ? "#ef4444"
                        : parseFloat(entry.percentage) > 5
                        ? "#f59e0b"
                        : "#10b981"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Resumo Estatístico Detalhado */}
      <div className="bg-zinc-900 rounded-lg p-6 border border-zinc-800">
        <h3 className="text-lg font-semibold text-zinc-100 mb-4">
          Resumo Estatístico Detalhado
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="text-left py-3 px-4 text-zinc-400 font-medium">
                  Coluna
                </th>
                <th className="text-right py-3 px-4 text-zinc-400 font-medium">
                  Mínimo
                </th>
                <th className="text-right py-3 px-4 text-zinc-400 font-medium">
                  Q25
                </th>
                <th className="text-right py-3 px-4 text-zinc-400 font-medium">
                  Mediana
                </th>
                <th className="text-right py-3 px-4 text-zinc-400 font-medium">
                  Q75
                </th>
                <th className="text-right py-3 px-4 text-zinc-400 font-medium">
                  Máximo
                </th>
                <th className="text-right py-3 px-4 text-zinc-400 font-medium">
                  Média
                </th>
                <th className="text-right py-3 px-4 text-zinc-400 font-medium">
                  Desvio Padrão
                </th>
              </tr>
            </thead>
            <tbody>
              {statistics.summary.map((stat) => (
                <tr
                  key={stat.column}
                  className="border-b border-zinc-800 hover:bg-zinc-800/50"
                >
                  <td className="py-3 px-4 text-zinc-100 font-medium">
                    {stat.column}
                  </td>
                  <td className="py-3 px-4 text-right text-zinc-300">
                    {stat.min !== null ? stat.min.toFixed(2) : "N/A"}
                  </td>
                  <td className="py-3 px-4 text-right text-zinc-300">
                    {stat.q25 !== null ? stat.q25.toFixed(2) : "N/A"}
                  </td>
                  <td className="py-3 px-4 text-right text-zinc-300">
                    {stat.q50 !== null ? stat.q50.toFixed(2) : "N/A"}
                  </td>
                  <td className="py-3 px-4 text-right text-zinc-300">
                    {stat.q75 !== null ? stat.q75.toFixed(2) : "N/A"}
                  </td>
                  <td className="py-3 px-4 text-right text-zinc-300">
                    {stat.max !== null ? stat.max.toFixed(2) : "N/A"}
                  </td>
                  <td className="py-3 px-4 text-right text-zinc-300">
                    {stat.avg !== null ? stat.avg.toFixed(2) : "N/A"}
                  </td>
                  <td className="py-3 px-4 text-right text-zinc-300">
                    {stat.stddev !== null ? stat.stddev.toFixed(2) : "N/A"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
