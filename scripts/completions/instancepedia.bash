# Bash completion for instancepedia
# Install: source this file or add to ~/.bashrc
#   source /path/to/instancepedia.bash
# Or copy to /etc/bash_completion.d/instancepedia

_instancepedia() {
    local cur prev words cword
    _init_completion || return

    local commands="list show search pricing regions compare cost-estimate compare-regions compare-family presets spot-history cache"
    local global_opts="--tui --debug --help"
    local common_opts="--region --profile --format --output --quiet --debug --help"
    local formats="table json csv"
    local storage_types="ebs-only instance-store"
    local nvme_opts="required supported unsupported"
    local processor_families="intel amd graviton"
    local network_perfs="low moderate high very-high"
    local pricing_models="on-demand spot savings-1yr savings-3yr"
    local sort_opts="vcpu memory price name"

    # Get the command (first non-option argument after instancepedia)
    local cmd=""
    local i
    for ((i=1; i < cword; i++)); do
        case "${words[i]}" in
            list|show|search|pricing|regions|compare|cost-estimate|compare-regions|compare-family|presets|spot-history|cache)
                cmd="${words[i]}"
                break
                ;;
        esac
    done

    # Handle subcommands for presets and cache
    local subcmd=""
    if [[ "$cmd" == "presets" ]] || [[ "$cmd" == "cache" ]]; then
        for ((i=1; i < cword; i++)); do
            case "${words[i]}" in
                list|apply|stats|clear)
                    subcmd="${words[i]}"
                    break
                    ;;
            esac
        done
    fi

    case "$prev" in
        --region)
            # Common AWS regions
            COMPREPLY=($(compgen -W "us-east-1 us-east-2 us-west-1 us-west-2 eu-west-1 eu-west-2 eu-west-3 eu-central-1 eu-north-1 ap-northeast-1 ap-northeast-2 ap-northeast-3 ap-southeast-1 ap-southeast-2 ap-south-1 sa-east-1 ca-central-1" -- "$cur"))
            return
            ;;
        --format)
            if [[ "$cmd" == "presets" ]] || [[ "$cmd" == "cache" ]]; then
                COMPREPLY=($(compgen -W "table json" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "$formats" -- "$cur"))
            fi
            return
            ;;
        --output)
            _filedir
            return
            ;;
        --storage-type)
            COMPREPLY=($(compgen -W "$storage_types" -- "$cur"))
            return
            ;;
        --nvme)
            COMPREPLY=($(compgen -W "$nvme_opts" -- "$cur"))
            return
            ;;
        --processor-family)
            COMPREPLY=($(compgen -W "$processor_families" -- "$cur"))
            return
            ;;
        --network-performance)
            COMPREPLY=($(compgen -W "$network_perfs" -- "$cur"))
            return
            ;;
        --pricing-model)
            COMPREPLY=($(compgen -W "$pricing_models" -- "$cur"))
            return
            ;;
        --sort-by)
            COMPREPLY=($(compgen -W "$sort_opts" -- "$cur"))
            return
            ;;
        --family|--instance-type)
            # Common instance families
            COMPREPLY=($(compgen -W "t2 t3 t3a t4g m5 m5a m5n m6i m6a m6g m7i m7a m7g c5 c5a c5n c6i c6a c6g c7i c7a c7g r5 r5a r5n r6i r6a r6g r7i r7a r7g i3 i3en i4i d2 d3 d3en h1 p3 p4d p5 g4dn g5 inf1 inf2 trn1" -- "$cur"))
            return
            ;;
        --regions)
            # Suggest common regions for compare-regions
            COMPREPLY=($(compgen -W "us-east-1,us-west-2 us-east-1,us-west-2,eu-west-1 us-east-1,eu-west-1,ap-northeast-1" -- "$cur"))
            return
            ;;
        --profile)
            # Try to get AWS profiles from config
            if [[ -f ~/.aws/credentials ]]; then
                local profiles=$(grep '^\[' ~/.aws/credentials | tr -d '[]')
                COMPREPLY=($(compgen -W "$profiles" -- "$cur"))
            fi
            return
            ;;
    esac

    # No command yet - suggest commands or global options
    if [[ -z "$cmd" ]]; then
        if [[ "$cur" == -* ]]; then
            COMPREPLY=($(compgen -W "$global_opts" -- "$cur"))
        else
            COMPREPLY=($(compgen -W "$commands" -- "$cur"))
        fi
        return
    fi

    # Handle subcommands
    case "$cmd" in
        presets)
            if [[ -z "$subcmd" ]]; then
                COMPREPLY=($(compgen -W "list apply" -- "$cur"))
            elif [[ "$subcmd" == "apply" ]]; then
                if [[ "$cur" == -* ]]; then
                    COMPREPLY=($(compgen -W "$common_opts --include-pricing" -- "$cur"))
                else
                    # Suggest preset names
                    COMPREPLY=($(compgen -W "web-server database compute-intensive gpu-ml arm-graviton burstable free-tier small-dev" -- "$cur"))
                fi
            elif [[ "$subcmd" == "list" ]]; then
                COMPREPLY=($(compgen -W "--format" -- "$cur"))
            fi
            return
            ;;
        cache)
            if [[ -z "$subcmd" ]]; then
                COMPREPLY=($(compgen -W "stats clear" -- "$cur"))
            elif [[ "$subcmd" == "stats" ]]; then
                COMPREPLY=($(compgen -W "--format --debug" -- "$cur"))
            elif [[ "$subcmd" == "clear" ]]; then
                COMPREPLY=($(compgen -W "--region --instance-type --force --quiet --debug" -- "$cur"))
            fi
            return
            ;;
        list)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$common_opts --search --free-tier-only --family --storage-type --nvme --processor-family --network-performance --min-price --max-price --include-pricing" -- "$cur"))
            fi
            ;;
        show|pricing)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$common_opts --include-pricing" -- "$cur"))
            fi
            ;;
        search)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$common_opts --free-tier-only --family --storage-type --nvme --processor-family --network-performance --min-price --max-price --include-pricing" -- "$cur"))
            fi
            ;;
        regions)
            COMPREPLY=($(compgen -W "$common_opts" -- "$cur"))
            ;;
        compare)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$common_opts --include-pricing" -- "$cur"))
            fi
            ;;
        cost-estimate)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$common_opts --hours-per-month --months --pricing-model" -- "$cur"))
            fi
            ;;
        compare-regions)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "--regions --format --output --quiet --debug" -- "$cur"))
            fi
            ;;
        compare-family)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$common_opts --include-pricing --sort-by" -- "$cur"))
            fi
            ;;
        spot-history)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$common_opts --days" -- "$cur"))
            fi
            ;;
    esac
}

complete -F _instancepedia instancepedia
