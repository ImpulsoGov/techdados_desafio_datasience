# CAPACITY
def _calculate_recovered(row, params):
    """
    Estima casos recuperados da doença com base no acumulado de
    infecções, innfectados atual e óbitos acumulados.

    Params
    ------
    row : pd.Series
        Linha da tabela do Farol com dados de casos confirmados e taxa
        de notificação mais recentes.
    params : Dict
        Dicionário de parâmetros de entrada do simulador para inserção
        de recuperados (R).

    Returns
    -------
    params : Dicionário atualizado com recuperados (R).
    """
    confirmed_adjusted = int(row[["confirmed_cases"]].sum() / row["notification_rate"])

    if confirmed_adjusted == 0:  # dont have any cases yet
        params["population_params"]["R"] = 0
        return params

    params["population_params"]["R"] = (
        confirmed_adjusted
        - params["population_params"]["I"]
        - params["population_params"]["D"]
    )

    if params["population_params"]["R"] < 0:
        params["population_params"]["R"] = (
            confirmed_adjusted - params["population_params"]["D"]
        )

    return params


def prepare_simulation(row, place_id, config, place_specific_params):
    """
    Calcula indicador de capacidade hospitalar 

    Params
    ------
    row : pd.Series
        Linha da tabela do Farol
    place_id : str
        Nível para cálculo: regional de saúde/estado [ health_regio_id | state_num_id ]
    config : Dict
        Dicionário de configuração com parâmetros fixos
    place_specific_params : pd.Dataframe
        Tabela de taxa de hospitalização e mortalidade calculada por
        regional de saúde/estado
        
    Returns
    -------
    params : Dicionário de parâmetros de entrada do simulador.
    """
    if place_id == "health_region_id":
        rt_upper = 
        place_specific_params = pd.read_csv("http://datasource.coronacidades.org/br/health_region_id/parameters").set_index(
            place_id
        )

    if place_id == "state_num_id":
        rt_upper = None
        place_specific_params = pd.read_csv("http://datasource.coronacidades.org/br/states/parameters").set_index(
            place_id
        )

    # based on Alison Hill: 40% asymptomatic
    symtomatic = [
        int(
            row["active_cases"]
            * (1 - config["br"]["seir_parameters"]["asymptomatic_proportion"])
        )
        if not np.isnan(row["active_cases"])
        else 1
    ][0]

    # Set parameters for the model
    params = {
        "population_params": {
            "N": int(row["population"]),
            "I": symtomatic,
            "D": [int(row["deaths"]) if not np.isnan(row["deaths"]) else 0][0],
        },
        "place_specific_params": {
            "fatality_ratio": place_specific_params["fatality_ratio"].loc[
                int(row.name)
            ],
            "i1_percentage": place_specific_params["i1_percentage"].loc[int(row.name)],
            "i2_percentage": place_specific_params["i2_percentage"].loc[int(row.name)],
            "i3_percentage": place_specific_params["i3_percentage"].loc[int(row.name)],
        },
        "n_beds": row["number_beds"]
        * config["br"]["simulacovid"]["resources_available_proportion"],
        "n_icu_beds": row["number_icu_beds"]
        * config["br"]["simulacovid"]["resources_available_proportion"],
        "R0": {
            "best": row["rt_most_likely"],  # Só usamos o "best" com o valor + provável do Rt para classificação do indicador
            "worst": row["rt_high_95"],
        },
    }

    # Doens't have projection: if notification rate null or zero
    if row["notification_rate"] != row["notification_rate"]:
        return np.nan
    if row["notification_rate"] == 0:
        return np.nan

    # Select Rt (effective reproduction number) of the state if heath
    # region doesn't have enough days for calculation
    if row["rt_most_likely"] != row["rt_most_likely"]:
        if place_id == "health_region_id":
            rt_upper = pd.read_csv("http://datasource.coronacidades.org/br/states/rt")
            rt = rt_upper.query(f"state_num_id == {row['state_num_id']}")
        else:
            return np.nan

        if len(rt) > 0:
            rt = rt.assign(
                last_updated=lambda df: pd.to_datetime(df["last_updated"])
            ).query("last_updated == last_updated.max()")
            params["R0"] = {"best": rt["Rt_most_likely"], "worst": rt["Rt_high_95"]}
        else:
            return np.nan

    # Calculate recovered
    params = _calculate_recovered(row, params)
    # Run simulation
    # dday = run_simulation(params, config)
    # return dday["beds"]["best"]
    return params