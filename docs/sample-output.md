# Sample Output

This output comes from the committed example config and fake bill total used by
`demo.py`, so it contains no real tenant or account data.

```text
Config: config/tenants.example.yaml
Method: fixed_percent   Total: $247.86

Unit  Tenant          Weight          Owes
------------------------------------------
A     Tenant One      40        $    99.14
B     Tenant Two      35        $    86.75
C     Tenant Three    25        $    61.97
```

The charges add back to the bill total exactly: `99.14 + 86.75 + 61.97 = 247.86`.
