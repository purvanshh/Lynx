type Props = {
  probability: number;
};

export function ConfidenceMeter({ probability }: Props) {
  return <section><h2>Confidence</h2><p>{Math.round(probability * 100)}%</p></section>;
}
