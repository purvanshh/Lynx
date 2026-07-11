type Props = {
  name: string;
  probability: number;
};

export function ParticipantCard({ name, probability }: Props) {
  return (
    <section>
      <h2>{name}</h2>
      <p>Candidate probability: {probability.toFixed(2)}</p>
    </section>
  );
}
