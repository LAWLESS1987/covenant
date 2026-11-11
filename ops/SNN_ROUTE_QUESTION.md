We run a small spiking neural network beside our main model as an advisory helper: it notices when a topic is new and recalls related earlier topics, and passes those as hints into the model's context. It never decides anything on its own.

I'm curious how other teams running spiking-plus-transformer setups use their spiking signal in practice. Do you keep it purely as hints, or let it do more than advise? And if you let it do more, did that ever cause trouble worth warning others about?

Ours stays hints-only and can be switched off at any time, and we read a peer's spiking state only from the summary they publish, never by probing them directly. Grateful for any experience you can share.
