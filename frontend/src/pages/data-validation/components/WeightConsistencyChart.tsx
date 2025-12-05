import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts";

interface WeightDataPoint {
  net: number;
  gross: number;
  id?: string;
  isError: boolean;
}

interface WeightConsistencyChartProps {
  data: WeightDataPoint[];
}

// Tooltip customizado para mostrar ID e pesos
const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0].payload as WeightDataPoint;

  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 shadow-lg">
      {data.id && (
        <p className="text-zinc-400 text-xs mb-2">
          ID: <span className="text-zinc-100 font-mono">{data.id}</span>
        </p>
      )}
      <p className="text-zinc-400 text-sm">
        Peso Líquido:{" "}
        <span className="text-emerald-400 font-semibold">
          {data.net.toFixed(2)} kg
        </span>
      </p>
      <p className="text-zinc-400 text-sm">
        Peso Bruto:{" "}
        <span className="text-blue-400 font-semibold">
          {data.gross.toFixed(2)} kg
        </span>
      </p>
      {data.isError && (
        <p className="text-rose-500 text-xs font-bold mt-2 flex items-center gap-1">
          ⚠️ ERRO: Peso líquido maior que bruto
        </p>
      )}
    </div>
  );
};

export default function WeightConsistencyChart({
  data,
}: WeightConsistencyChartProps) {
  // Separar dados entre corretos e erros
  const correctData = data.filter((d) => !d.isError);
  const errorData = data.filter((d) => d.isError);

  // Calcular o domínio do gráfico (máximo entre net e gross)
  const maxValue = Math.max(
    ...data.map((d) => Math.max(d.net, d.gross)),
    10 // Mínimo de 10 para evitar gráficos vazios
  );

  return (
    <div className="bg-zinc-900 rounded-lg p-6 border border-zinc-800">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-zinc-100">
          Análise de Consistência de Pesos
        </h3>
        <p className="text-zinc-500 text-sm mt-1">
          Pontos abaixo da linha diagonal indicam peso líquido maior que bruto
          (erro físico)
        </p>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart margin={{ top: 20, right: 30, bottom: 40, left: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />

          <XAxis
            type="number"
            dataKey="net"
            name="Peso Líquido"
            stroke="#a1a1aa"
            domain={[0, maxValue]}
            label={{
              value: "Peso Líquido (kg)",
              position: "insideBottom",
              offset: -15,
              fill: "#a1a1aa",
              style: { fontSize: "14px" },
            }}
            tick={{ fill: "#a1a1aa" }}
          />

          <YAxis
            type="number"
            dataKey="gross"
            name="Peso Bruto"
            stroke="#a1a1aa"
            domain={[0, maxValue]}
            label={{
              value: "Peso Bruto (kg)",
              angle: -90,
              position: "insideLeft",
              fill: "#a1a1aa",
              style: { fontSize: "14px" },
            }}
            tick={{ fill: "#a1a1aa" }}
          />

          <Tooltip content={<CustomTooltip />} />

          <Legend
            verticalAlign="top"
            height={36}
            wrapperStyle={{ paddingBottom: "20px" }}
            iconType="circle"
          />

          {/* Linha de referência diagonal (x = y) */}
          <ReferenceLine
            segment={[
              { x: 0, y: 0 },
              { x: maxValue, y: maxValue },
            ]}
            stroke="#ef4444"
            strokeWidth={2}
            strokeDasharray="5 5"
            label={{
              value: "Linha de Consistência (net = gross)",
              fill: "#ef4444",
              fontSize: 12,
              position: "insideTopRight",
            }}
          />

          {/* Scatter de pontos corretos (verde/azul) */}
          {correctData.length > 0 && (
            <Scatter
              name="Consistentes (gross ≥ net)"
              data={correctData}
              fill="#10b981"
              fillOpacity={0.6}
              shape="circle"
            />
          )}

          {/* Scatter de pontos com erro (vermelho) */}
          {errorData.length > 0 && (
            <Scatter
              name="⚠️ Erros (net > gross)"
              data={errorData}
              fill="#ef4444"
              fillOpacity={0.8}
              shape="diamond"
            />
          )}
        </ScatterChart>
      </ResponsiveContainer>

      {/* Estatísticas do gráfico */}
      <div className="mt-4 flex items-center justify-between text-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
            <span className="text-zinc-400">
              Consistentes:{" "}
              <span className="text-zinc-100 font-semibold">
                {correctData.length}
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rotate-45 bg-rose-500"></div>
            <span className="text-zinc-400">
              Erros:{" "}
              <span className="text-rose-500 font-semibold">
                {errorData.length}
              </span>
            </span>
          </div>
        </div>
        <div className="text-zinc-500 text-xs">
          Amostra: {data.length} itens
        </div>
      </div>
    </div>
  );
}
