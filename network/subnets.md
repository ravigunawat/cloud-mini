# Subnet plan for 10.20.0.0/16 (largest first, contiguous)

| Subnet | Hosts needed | Prefix | Network | Usable range | Broadcast | Usable hosts |
|---|---|---|---|---|---|---|
| app | 1,000 | /22 | 10.20.0.0 | 10.20.0.1 - 10.20.3.254 | 10.20.3.255 | 1,022 |
| public | 250 | /24 | 10.20.4.0 | 10.20.4.1 - 10.20.4.254 | 10.20.4.255 | 254 |
| data | 100 | /25 | 10.20.5.0 | 10.20.5.1 - 10.20.5.126 | 10.20.5.127 | 126 |
| management | 20 | /27 | 10.20.5.128 | 10.20.5.129 - 10.20.5.158 | 10.20.5.159 | 30 |

## Working
usable = 2^(32-prefix) - 2
- app: /23 gives 510 (too small), /22 gives 1022 (fits).
- public: /24 gives 254 (fits 250; /25 gives only 126).
- data: /25 gives 126 (fits 100; /26 gives only 62).
- management: /27 gives 30 (fits 20; /28 gives only 14).
Each starts right after the previous one: app ends 10.20.3.255, public 10.20.4.0-4.255, data 10.20.5.0-5.127, management 10.20.5.128-5.159.
