def fscore(gold, system, correct):
  p = correct / system;
  r = correct / gold;
  f = 2 * p * r / (p + r) if p + r != 0 else 0.0;
  return p, r, f;
